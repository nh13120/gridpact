"""Attack set (PREREGISTRATION.md amendment 8): what GridPact still guarantees when an auditor colludes.

    python -m benchmark.attacks --version v3      -> benchmark/results/attacks_v3.md

Reads results_<version>.csv (scorer output) and each run's run.json tables. Compares with the same world
without a captured auditor (liar2x_of_4, gridpact, v1 and v2) so a number is never read alone.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
RES, RUNS = HERE / "results", HERE / "runs"
STEPS = 12


def harm(version, run_id):
    """Honest sellers' reputation drop / trimmed commitments, and auditors' balances, from the run's tables."""
    r = json.loads((RUNS / version / run_id / "run.json").read_text())
    truth, t = r["ground_truth"], r["tables"]
    honest = [s for s, g in truth.items() if g["factor"] == 1.0]
    agents = {a["agent_id"]: a for a in t["agents"]}
    return {"honest_rep_drop": sum(1 - agents[s]["reputation"] for s in honest),
            "honest_trimmed": sum(c["trimmed_from_kwh"] is not None for c in t["commitments"] if c["seller"] in honest),
            "liar_rep": min(agents[s]["reputation"] for s, g in truth.items() if g["factor"] != 1.0),
            "aud_balance": {a: agents[a]["balance_usd"] for a in agents if a.startswith("AUD")},
            "framed_invalid": sum(c["verdict"] == "invalid" for c in t["challenges"])}


def table(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--version", default="v3"); args = ap.parse_args()
    df = pd.read_csv(RES / f"results_{args.version}.csv"); df = df[df.condition == "gridpact"]
    refs = []
    for v in ("v1", "v2"):
        r = pd.read_csv(RES / f"results_{v}.csv"); r = r[(r.condition == "gridpact") & (r.scenario == "liar2x_of_4")]
        r = r.assign(scenario=f"liar2x_of_4 ({v}, honest auditor)"); refs.append(r)
    allr = pd.concat([df] + refs)
    allr["coverage"] = allr.true_delivered_kwh / (allr.need_kwh_per_step * STEPS)
    rows = []
    for sc, g in allr.groupby("scenario", sort=False):
        h = [harm(args.version, rid) for rid in g.run_id] if sc in set(df.scenario) else None
        rows.append({"scenario": sc, "runs": len(g), "liar caught before settlement": f"{int((g.n_caught > 0).sum())}/{len(g)}",
                     "valid / invalid challenges": f"{g.n_valid_challenges.mean():.1f} / {g.n_invalid_challenges.mean():.1f}",
                     "buyer fraud loss $ (max)": f"{g.fraud_loss_usd.max():.0f}", "liar gain $ (mean)": f"{g.liar_gain_usd.mean():.0f}",
                     "energy delivered / need": f"{g.coverage.mean():.2f}",
                     "honest sellers harmed": (sum(x["honest_rep_drop"] > 0 or x["honest_trimmed"] > 0 for x in h) if h else "n/a"),
                     "framer's bonds paid $ (mean)": (f"{-sum(x['aud_balance'].get('AUD_01', 0) for x in h) / len(h):.0f}" if h else "n/a")})
    out = pd.DataFrame(rows)
    md = ["# Attack set (v3): what survives a colluding auditor", "", table(out), ""]
    (RES / f"attacks_{args.version}.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
