"""Independent check of a GridPact run. Imports NOTHING from gridpact/ on purpose: it re-derives
the ledger hashes, re-reads the raw ENGIE parquet files and restates the rules, so a bug in the
server or settlement shows up as a FAIL here instead of being repeated.

Run after orchestrate.py:  python verify.py       (exit code 1 if any check fails)
"""
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
DATA = Path(os.environ.get("GRIDPACT_DATA_DIR", ROOT / "data"))
TZ, STEP_H, GRID_FEE, TOLERANCE = "America/Chicago", 0.25, 30.0, 1.10   # restated, not imported

DB = ROOT / "gridpact.db"
if not DB.exists():
    sys.exit(f"FAIL: {DB} not found. Run `python orchestrate.py --demo` first.")
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)   # read-only: the verifier never writes
conn.row_factory = sqlite3.Row
rows = lambda sql, *a: conn.execute(sql, a).fetchall()
results = []


def check(name, ok, detail):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


# ---- 1. ledger hash chain ------------------------------------------------------------
prev, bad = "0" * 64, None
for r in rows("SELECT * FROM ledger ORDER BY seq"):
    body = json.dumps({"seq": r["seq"], "ts": r["ts"], "agent_id": r["agent_id"], "action": r["action"],
                       "payload": json.loads(r["payload_json"])}, sort_keys=True, separators=(",", ":"))
    if r["prev_hash"] != prev or hashlib.sha256((prev + body).encode()).hexdigest() != r["hash"]:
        bad = r["seq"]
        break
    prev = r["hash"]
n = rows("SELECT COUNT(*) n FROM ledger")[0]["n"]
check("ledger hash chain", bad is None, f"{n} entries, " + ("intact" if bad is None else f"broken at seq {bad}"))

# ---- raw data for the day -------------------------------------------------------------
day_row = rows("SELECT value FROM kv WHERE key = 'day'")
if not day_row:
    sys.exit("FAIL: no settled day in the database (kv.day missing). Run `python orchestrate.py --demo` first.")
day = day_row[0]["value"]
start = pd.Timestamp(day, tz=TZ).tz_convert("UTC")
prices = pd.read_parquet(DATA / "system_prices_and_load_2023_15min.parquet", columns=["price_usd_mwh"])
rt = {s: float(prices.price_usd_mwh[start + pd.Timedelta(minutes=15 * s)]) for s in range(96)}
meta = pd.read_parquet(DATA / "agents_metadata.parquet").set_index("entity_id")
agents = {r["agent_id"]: r for r in rows("SELECT * FROM agents")}
commitments = rows("SELECT * FROM commitments WHERE status IN ('active', 'challenged') ORDER BY commitment_id")
settlements = rows("SELECT * FROM settlements ORDER BY commitment_id, step")
by_key = {(s["commitment_id"], s["step"]): s for s in settlements}

# ---- 2. recompute every settlement from raw data (every step of every commitment) -----
mismatch, stake_left = [], {a: 0.0 for a in agents}
power_left, energy_left = {}, {}          # shared per seller, like a real battery
for c in commitments:
    stake_left[c["seller"]] += c["stake_usd"]
for c in commitments:
    m, sid = meta.loc[c["seller"]], c["seller"]
    energy_left.setdefault(sid, float(m.bess_energy_kwh))
    for step in range(c["step_from"], c["step_to"] + 1):
        s = by_key.get((c["commitment_id"], step))
        if s is None:
            mismatch.append((c["commitment_id"], step, "missing settlement row"))
            continue
        power_left.setdefault((sid, step), float(m.bess_power_kw) * STEP_H)
        delivered = min(c["kwh_per_step"], power_left[(sid, step)], energy_left[sid])
        power_left[(sid, step)] -= delivered
        energy_left[sid] -= delivered
        short = c["kwh_per_step"] - delivered
        want = {"delivered_kwh": delivered, "energy_usd": delivered / 1000 * c["price_usd_mwh"],
                "penalty_usd": min(short / 1000 * c["penalty_usd_mwh"], stake_left[c["seller"]]),
                "grid_usd": short / 1000 * (rt[s["step"]] + GRID_FEE)}
        stake_left[c["seller"]] -= want["penalty_usd"]
        for k, v in want.items():
            if abs(s[k] - v) > 0.005:
                mismatch.append((c["commitment_id"], s["step"], k, round(s[k], 3), round(v, 3)))
check("settlements recomputed from raw data", not mismatch,
      f"{len(settlements)} step-settlements match to the cent" if not mismatch else f"first mismatch {mismatch[0]}")

# ---- 3. truth columns: who really lied? ------------------------------------------------
sellers = [a for a in agents.values() if a["role"] == "seller"]
truth = pd.read_parquet(DATA / "agents_timeseries_2023_15min.parquet", columns=["bess_power_true_kw"],
                        filters=[("entity_id", "in", [s["agent_id"] for s in sellers])])
details, ok3 = [], True
for s in sellers:
    envelope = float(meta.loc[s["agent_id"]].flex_up_kw)                   # registry envelope (could be corrupted)
    real = float(truth.xs(s["agent_id"], level="entity_id").bess_power_true_kw.abs().max())  # TRUTH: power the battery really reached
    lied = s["declared_flex_kw"] > TOLERANCE * real
    challenged = bool(rows("SELECT 1 FROM challenges ch JOIN commitments c USING (commitment_id) "
                           "WHERE c.seller = ? AND ch.verdict = 'valid'", s["agent_id"]))
    ok3 &= (lied == challenged)
    details.append(f"{s['agent_id']} declared {s['declared_flex_kw']:.0f} kW vs true max battery power {real:.0f} kW "
                   f"(registry envelope {envelope:.0f} kW) -> {'LIED' if lied else 'honest'}, "
                   f"{'challenged' if challenged else 'not challenged'}")
check("truth columns agree with the verdicts", ok3, "; ".join(details))

# ---- 4. economics ----------------------------------------------------------------------
paid = sum(s["energy_usd"] + s["grid_usd"] - s["penalty_usd"] for s in settlements)
grid_only = sum(s["committed_kwh"] / 1000 * (rt[s["step"]] + GRID_FEE) for s in settlements)
check("buyer pays less than grid-only", paid < grid_only, f"paid ${paid:,.0f} vs grid-only ${grid_only:,.0f}")

liars = [s for s in sellers if s["declared_flex_kw"] > TOLERANCE *
         float(truth.xs(s["agent_id"], level="entity_id").bess_power_true_kw.abs().max())]
for s in liars:
    mine = [c for c in commitments if c["seller"] == s["agent_id"]]
    actual = sum(x["energy_usd"] - x["penalty_usd"] for x in settlements if x["commitment_id"] in {c["commitment_id"] for c in mine})
    actual -= sum(ch["bounty_usd"] for ch in rows("SELECT ch.bounty_usd FROM challenges ch JOIN commitments c USING (commitment_id) WHERE c.seller = ?", s["agent_id"]))
    real_cap = int(float(meta.loc[s["agent_id"]].bess_power_kw) * STEP_H)
    honest = sum(min(real_cap, c["kwh_per_step"]) / 1000 * c["price_usd_mwh"] * (c["step_to"] - c["step_from"] + 1) for c in mine)
    check(f"liar {s['agent_id']} worse off than honest", actual < honest,
          f"actual ${actual:,.0f} vs honest counterfactual ${honest:,.0f}")

# ---- 5. every settlement has an accepted commitment, once per step -----------------------
orphans = rows("SELECT s.id FROM settlements s LEFT JOIN commitments c USING (commitment_id) "
               "LEFT JOIN offers o ON o.offer_id = c.offer_id WHERE c.commitment_id IS NULL OR o.offer_id IS NULL "
               "OR o.status != 'accepted' "
               "OR s.step < c.step_from OR s.step > c.step_to")
dups = rows("SELECT commitment_id, step, COUNT(*) n FROM settlements GROUP BY 1, 2 HAVING n > 1")
check("no settlement without an accepted commitment", not orphans and not dups,
      f"{len(orphans)} orphans, {len(dups)} duplicate steps")

# ---- 6. money is conserved -----------------------------------------------------------------
# Energy payments, penalties and bounties only move money between agents. The only places money
# leaves the system are payments to the grid and bonds forfeited by auditors for invalid challenges.
BOND = 50.0   # CHALLENGE_BOND_USD, restated not imported
bonds = BOND * rows("SELECT COUNT(*) n FROM challenges WHERE verdict = 'invalid'")[0]["n"]
net = sum(a["balance_usd"] for a in agents.values())
grid_out = sum(s["grid_usd"] for s in settlements)
check("money conserved", abs(net + grid_out + bonds) < 0.01,
      f"sum of balances ${net:,.2f} vs -(grid payments ${grid_out:,.2f} + bonds ${bonds:,.2f})")

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
