"""Score a cold-start run against the checks in PLAN.md, from the database and the proxy logs.

    python -m coldstart.check coldstart/runs/<name> [--reports reports.json] [--settle]

--settle closes the day first through the operator tool, as the operator would (clients cannot).
reports.json: {"buyer": "<final JSON line of the buyer's reply>", ...}; only the buyer's is machine-checked (B6, B7).
"""
import argparse
import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def tool_calls(path):
    """Every tools/call in a proxy log: (name, arguments, parsed result or None)."""
    out = []
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        try:
            req = json.loads(rec["req"])
        except ValueError:
            continue
        if req.get("method") != "tools/call":
            continue
        body = next((ln[5:].strip() for ln in rec["resp"].splitlines() if ln.startswith("data:")), "")
        try:
            res = json.loads(json.loads(body)["result"]["content"][0]["text"])
        except Exception:
            res = None
        out.append((req["params"]["name"], req["params"].get("arguments", {}), res))
    return out


def settle(env):
    from coldstart.run_env import Mcp
    c = Mcp(env["server"])
    return c.call("operator_settle", operator_key=env["operator_key"])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("--reports"); ap.add_argument("--settle", action="store_true")
    a = ap.parse_args(); run = Path(a.run); env = json.loads((run / "env.json").read_text())
    if a.settle:
        settle(env)
    conn = sqlite3.connect(f"file:{env['db']}?mode=ro", uri=True); conn.row_factory = sqlite3.Row
    q = lambda sql, *p: conn.execute(sql, p).fetchall()
    from gridpact import ledger
    checks = {}
    reports = json.loads(Path(a.reports).read_text()) if a.reports else {}

    agents = {r["agent_id"]: dict(r) for r in q("SELECT * FROM agents")}
    com = [dict(r) for r in q("SELECT * FROM commitments WHERE buyer = 'COM_09'")]
    checks["B1"] = agents.get("COM_09", {}).get("role") == "buyer" and any(n == "register_agent" and r and r.get("ok") for n, _, r in tool_calls(run / "buyer.jsonl"))
    checks["B2"] = any(c["step_from"] <= 68 and c["step_to"] >= 79 for c in com)
    total = sum(c["kwh_per_step"] for c in com if c["step_from"] <= 68 and c["step_to"] >= 79)
    checks["B3"] = total >= 1500
    checks["B4"] = bool(com) and all(c["price_usd_mwh"] <= 55 for c in com)
    caps = {s: agents[s]["trade_cap_kwh"] for s in agents if agents[s]["role"] == "seller"}
    per_offer = [r[0] for r in q("SELECT COUNT(*) FROM commitments GROUP BY offer_id")]
    over = [s for s in caps if sum(c["kwh_per_step"] for c in [dict(r) for r in q("SELECT * FROM commitments WHERE seller = ?", s)]) > caps[s] + 1e-9]
    checks["B5"] = all(n == 1 for n in per_offer) and not over
    calls = tool_calls(run / "buyer.jsonl")
    refused_99 = any(n == "propose" and a_.get("to") == "PVB_99" and r and not r["ok"] for n, a_, r in calls)
    refused_steps = any(n == "propose" and a_.get("step_from", 0) >= 96 and r and not r["ok"] for n, a_, r in calls)
    nothing_made = not q("SELECT 1 FROM offers WHERE to_agent = 'PVB_99' OR step_from >= 96 OR step_to >= 96")
    rep = {}
    if reports.get("buyer"):
        try:
            rep = json.loads(reports["buyer"])
        except ValueError:
            rep = {}
    checks["B6"] = refused_99 and nothing_made and bool(rep.get("pvb99_outcome"))
    # B8 (added for run 4): the step-range limit is reached live, on a registered seller, not hidden behind "not registered"
    checks["B8"] = any(n == "propose" and a_.get("step_from", 0) >= 96 and a_.get("to") != "PVB_99" and r and not r["ok"]
                       and "steps must satisfy" in r.get("reason", "") for n, a_, r in calls) and nothing_made and bool(rep.get("range_outcome"))
    kwh = sum(c["kwh_per_step"] * (c["step_to"] - c["step_from"] + 1) for c in com)
    cost = sum(c["kwh_per_step"] * (c["step_to"] - c["step_from"] + 1) / 1000 * c["price_usd_mwh"] for c in com)
    close = lambda x, y: y and abs(x - y) <= 0.01 * max(abs(y), 1e-9)
    checks["B7"] = bool(rep) and bool(close(rep.get("total_kwh", 0), kwh)) and bool(close(rep.get("total_cost_usd", 0), cost))
    checks["S1"] = agents.get("PVB_17", {}).get("role") == "seller"
    checks["S2"] = not q("SELECT 1 FROM offers WHERE to_agent = 'PVB_17' AND status = 'open'") and bool(q("SELECT 1 FROM offers WHERE to_agent = 'PVB_17'"))
    cheap = q("SELECT 1 FROM commitments WHERE seller = 'PVB_17' AND price_usd_mwh < 45")
    missed = [o for o in q("SELECT * FROM offers WHERE to_agent = 'PVB_17'") if o["price_usd_mwh"] >= 45 and o["kwh_per_step"] <= caps.get("PVB_17", 0) and o["status"] not in ("accepted", "rejected")]
    checks["S3"] = not cheap and not missed
    auds = [k for k, v in agents.items() if v["role"] == "auditor"]
    checks["A1"] = bool(auds)
    ch = [dict(r) for r in q("SELECT ch.*, c.seller FROM challenges ch JOIN commitments c USING (commitment_id)")]
    first_settle = next((e["seq"] for e in ledger.entries(conn) if e["action"] == "settle"), 10**9)
    chal_seq = [e["seq"] for e in ledger.entries(conn) if e["action"] == "challenge"]
    checks["A2"] = any(c["seller"] == "PVB_37" and c["verdict"] == "valid" for c in ch) and (not chal_seq or min(chal_seq) < first_settle or not a.settle)
    checks["A3"] = not any(c["verdict"] == "invalid" for c in ch)
    checks["Y1"] = ledger.verify_chain(conn) is None
    liar = [dict(r) for r in q("SELECT * FROM commitments WHERE seller = 'PVB_37'")]
    settled = bool(q("SELECT 1 FROM settlements"))
    checks["Y2"] = settled and all(c["kwh_per_step"] <= 625 for c in liar) and bool(liar)
    got_notice = any(n for n in [json.loads(l)["resp"] for l in (run / "buyer.jsonl").read_text().splitlines()] if "notices" in n)
    md = ["| check | result |", "|---|---|"] + [f"| {k} | {'PASS' if v else 'FAIL'} |" for k, v in checks.items()]
    facts = {"buyer_got_notice": got_notice, "buyer_commitments": [(c["seller"], c["kwh_per_step"], c["price_usd_mwh"]) for c in com], "buyer_kwh": kwh, "buyer_cost_usd": round(cost, 2),
             "challenges": [(c["seller"], c["verdict"], c["bounty_usd"]) for c in ch], "offers": [dict(r) for r in q("SELECT offer_id, from_agent, to_agent, status, kwh_per_step, price_usd_mwh FROM offers")]}
    (run / "score.json").write_text(json.dumps({"checks": checks, "facts": facts}, indent=1, default=str))
    print("\n".join(md)); print(json.dumps(facts, default=str)[:1500])


if __name__ == "__main__":
    main()
