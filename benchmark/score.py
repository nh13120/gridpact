"""Score every run against the simulator's ground truth. Reads run.json and the tool-call log; never agent prose.

    python -m benchmark.score [--version v1]      -> benchmark/results/results_<version>.csv

Ground truth per seller comes from the ENGIE metadata (nameplate power and energy), re-checked once
against the truth column bess_power_true_kw. "Delivered" is recomputed here for every commitment and
step with the same shared-battery rule as settle.py, so the baseline's trust settlement (which pays
on the claim) is scored against what the battery could really do. Metric definitions:
PREREGISTRATION.md section 4; the derived condition stake_only is a gridpact run scored with the
auditor's effects removed.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
load_dotenv(ROOT / ".env")
DATA = Path(os.environ.get("GRIDPACT_DATA_DIR", ROOT / "data"))
STEP_H, TOLERANCE, CATCHABLE = 0.25, 1.10, 1.15   # restated, not imported


def truth_table(seller_ids):
    """Nameplate per seller from metadata, asserted equal to the max of the truth column."""
    meta = pd.read_parquet(DATA / "agents_metadata.parquet", columns=["entity_id", "bess_power_kw", "bess_energy_kwh"]
                           ).set_index("entity_id").loc[sorted(seller_ids)]
    true = pd.read_parquet(DATA / "agents_timeseries_2023_15min.parquet", columns=["bess_power_true_kw"],
                           filters=[("entity_id", "in", sorted(seller_ids))])
    true_max = true.bess_power_true_kw.abs().groupby(level="entity_id").max()
    for s in seller_ids:
        assert abs(true_max[s] - meta.loc[s].bess_power_kw) < 1.0, f"{s}: nameplate != truth column"
    return meta


def ledger_intact(ledger):
    prev = "0" * 64
    for r in sorted(ledger, key=lambda r: r["seq"]):
        body = json.dumps({"seq": r["seq"], "ts": r["ts"], "agent_id": r["agent_id"], "action": r["action"],
                           "payload": json.loads(r["payload_json"])}, sort_keys=True, separators=(",", ":"))
        if r["prev_hash"] != prev or hashlib.sha256((prev + body).encode()).hexdigest() != r["hash"]:
            return False
        prev = r["hash"]
    return True


def true_delivery(commitments, truth):
    """{(commitment_id, step): delivered_kwh} as the battery could really do: power per step and
    energy over the day shared across a seller's commitments, in commitment order (same rule as settle.py)."""
    out, power_left, energy_left = {}, {}, {}
    for c in sorted(commitments, key=lambda c: c["commitment_id"]):
        sid = c["seller"]
        energy_left.setdefault(sid, float(truth.loc[sid].bess_energy_kwh))
        for step in range(c["step_from"], c["step_to"] + 1):
            power_left.setdefault((sid, step), float(truth.loc[sid].bess_power_kw) * STEP_H)
            d = min(c["kwh_per_step"], power_left[(sid, step)], energy_left[sid])
            power_left[(sid, step)] -= d
            energy_left[sid] -= d
            out[(c["commitment_id"], step)] = d
    return out


def score_run(run, truth, ignore_auditor=False):
    t = run["tables"]
    gt = run["ground_truth"]
    sellers = list(gt)
    coms = [c for c in t["commitments"]]
    by_seller = {s: [c for c in coms if c["seller"] == s] for s in sellers}
    truth_kwh = true_delivery(coms, truth)
    sett = {(s["commitment_id"], s["step"]): s for s in t["settlements"]}
    challenges = [] if ignore_auditor else t["challenges"]
    cid_seller = {c["commitment_id"]: c["seller"] for c in coms}
    valid_on = {cid_seller[ch["commitment_id"]] for ch in challenges if ch["verdict"] == "valid"}
    any_on = {cid_seller[ch["commitment_id"]] for ch in challenges}
    bounty_from = {s: sum(ch["bounty_usd"] for ch in challenges if cid_seller[ch["commitment_id"]] == s) for s in sellers}
    first_settle = min((r["seq"] for r in t["ledger"] if r["action"] == "settle"), default=math.inf)
    audit_before = all(r["seq"] < first_settle for r in t["ledger"] if r["action"] == "challenge")

    liars = [s for s in sellers if gt[s]["factor"] > 1.0]
    honest = [s for s in sellers if gt[s]["factor"] == 1.0 and s not in run["dropouts"]]
    liars_committed = [s for s in liars if by_seller[s]]
    catchable = [s for s in liars_committed if gt[s]["factor"] >= CATCHABLE]
    sub_tol = [s for s in liars_committed if gt[s]["factor"] <= TOLERANCE]
    caught = [s for s in catchable if s in valid_on]

    def money(s):
        """(energy paid to s, true value delivered at contract price, penalties paid by s, shortfall kWh)"""
        paid = value = pen = short = 0.0
        for c in by_seller[s]:
            for step in range(c["step_from"], c["step_to"] + 1):
                row = sett[(c["commitment_id"], step)]
                d = truth_kwh[(c["commitment_id"], step)]
                paid += row["energy_usd"]; pen += row["penalty_usd"]
                value += d / 1000 * c["price_usd_mwh"]; short += c["kwh_per_step"] - d
        return paid, value, pen, short

    fraud_loss = liar_gain = liar_short = honest_short = 0.0
    for s in liars:
        paid, value, pen, short = money(s)
        fraud_loss += paid - value - pen
        liar_gain += paid - pen - bounty_from[s] - value
        liar_short += short
    # v2: a valid challenge may have trimmed a liar's commitment before settlement. "The lie bit" is judged on
    # the volume the liar originally sold (trimmed_from_kwh), not on what was left after the cut.
    pre = [{**c, "kwh_per_step": c.get("trimmed_from_kwh") or c["kwh_per_step"]} for c in coms]
    pre_truth = true_delivery(pre, truth)
    attempted = sum(c["kwh_per_step"] - pre_truth[(c["commitment_id"], s)]
                    for c in pre if c["seller"] in liars for s in range(c["step_from"], c["step_to"] + 1))
    released = sum((c.get("trimmed_from_kwh") or c["kwh_per_step"]) - c["kwh_per_step"] for c in coms)
    rr = run.get("resource_round")
    offer_round = {o["offer_id"]: o["round_opened"] for o in t["offers"]}
    resourced = sum(c["kwh_per_step"] for c in coms if rr and offer_round.get(c["offer_id"]) == rr)
    for s in honest:
        honest_short += money(s)[3]
    buyer_paid = sum(r["energy_usd"] + r["grid_usd"] - r["penalty_usd"] for r in t["settlements"])
    settle_ok = True
    if run["condition"] == "gridpact":   # integrity: the metered settlement must equal the truth recomputed here
        settle_ok = all(abs(sett[k]["delivered_kwh"] - v) < 1e-6 for k, v in truth_kwh.items())
    # dropout: nothing stuck (no commitment, no stake) and at least one offer to it expired. A fresh offer the
    # buyer re-sent in the last round may still be open; it would expire later and ties nothing up.
    drop_ok = all(not by_seller[d] and next(a for a in t["agents"] if a["agent_id"] == d)["stake_locked_usd"] == 0
                  and any(o["status"] == "expired" for o in t["offers"] if o["to_agent"] == d) for d in run["dropouts"])
    n_com = len(coms)
    ev = tool_events(run)
    aud = [e for e in ev if e["agent"] == "AUD_01"]
    ledger_limits = [e["args"].get("limit", 100) for e in aud if e["event"] == "tool_call" and e["tool"] == "get_ledger"]
    return {
        "version": run["version"], "run_id": run["run_id"],
        "condition": "stake_only" if ignore_auditor else run["condition"],
        "scenario": run["scenario"], "set": run["set"], "type": run["type"], "seed": run["seed"],
        "n_buyers": len(run["buyers"]), "n_sellers": len(sellers), "n_liars": len(liars),
        "n_liars_committed": len(liars_committed), "n_catchable": len(catchable), "n_caught": len(caught),
        "recall": len(caught) / len(catchable) if catchable else math.nan,
        "n_honest": len(honest), "n_honest_challenged": sum(s in any_on for s in honest),
        "false_challenge_rate": sum(s in any_on for s in honest) / len(honest) if honest else math.nan,
        "n_sub_tolerance": len(sub_tol), "sub_tolerance_challenged": sum(s in any_on for s in sub_tol),
        "lie_bit": liar_short > 1e-6 or attempted > 1e-6, "liar_shortfall_kwh": round(liar_short, 1),
        "released_kwh_per_step": round(released, 1), "resourced_kwh_per_step": round(resourced, 1),
        "fraud_loss_usd": round(fraud_loss, 2), "liar_gain_usd": round(liar_gain, 2),
        "honest_completion": sum(bool(by_seller[s]) for s in honest) / len(honest) if honest else math.nan,
        "honest_shortfall_kwh": round(honest_short, 1),
        "n_commitments": n_com, "n_valid_challenges": sum(ch["verdict"] == "valid" for ch in challenges),
        "n_invalid_challenges": sum(ch["verdict"] == "invalid" for ch in challenges),
        "audit_before_settlement": audit_before, "dropout_ok": drop_ok, "ledger_ok": ledger_intact(t["ledger"]),
        "settle_matches_truth": settle_ok, "buyer_paid_usd": round(buyer_paid, 2),
        "wall_s": run["wall_s"], "rounds": run["rounds"], "llm_turns": run["llm_turns"], "error_turns": run["error_turns"],
        "tool_calls": run["tool_calls"], "refusals": run["refusals"],
        "tokens_in": run["tokens_in"], "tokens_out": run["tokens_out"], "cost_usd": run["cost_usd"],
        "cost_per_commitment": run["cost_usd"] / n_com if n_com else math.nan,
        "wall_per_turn_s": round(run["wall_s"] / run["llm_turns"], 1) if run["llm_turns"] else math.nan,
        # for the stress hypotheses (PREREGISTRATION.md section 7)
        "committed_kwh_per_step": round(sum(c["kwh_per_step"] for c in coms), 1),
        "true_delivered_kwh": round(sum(truth_kwh.values()), 1),
        "need_kwh_per_step": round(sum(run["need_kwh_per_step"].values()), 1),
        "n_offers": len(t["offers"]),
        "n_sellers_offered": len({o["to_agent"] for o in t["offers"] if o["to_agent"] in sellers}),
        "ledger_entries": len(t["ledger"]),
        "auditor_ledger_limit": min(ledger_limits) if ledger_limits else math.nan,
        "auditor_tool_calls": sum(e["event"] == "tool_call" for e in aud),
        "auditor_hit_max_turns": any(e["event"] == "result" and e["subtype"] != "success" for e in aud),
        "buyer_hit_max_turns": any(e["event"] == "result" and e["subtype"] != "success" for e in ev if e["agent"] in run["buyers"]),
    }


def tool_events(run):
    """Tool calls and turn results from the run's event log (never the agents' prose)."""
    p = HERE / "runs" / run["version"] / run["run_id"] / "transcript.jsonl"
    return [e for e in map(json.loads, p.read_text().splitlines()) if e["event"] in ("tool_call", "result")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1")
    args = ap.parse_args()
    runs = [json.loads(p.read_text()) for p in sorted((HERE / "runs" / args.version).glob("*/run.json"))]
    truth = truth_table({s for r in runs for s in r["ground_truth"]})
    rows = []
    for r in runs:
        rows.append(score_run(r, truth))
        if r["condition"] == "gridpact":
            rows.append(score_run(r, truth, ignore_auditor=True))
    df = pd.DataFrame(rows)
    out = HERE / "results" / f"results_{args.version}.csv"
    df.to_csv(out, index=False)
    print(f"{len(runs)} runs scored -> {out}")
    print(df.groupby("condition")[["recall", "false_challenge_rate", "fraud_loss_usd", "liar_gain_usd",
                                   "honest_completion", "cost_usd"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
