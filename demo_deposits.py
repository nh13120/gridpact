"""A two-minute demo of GridPact's deposits and checks. No LLM, no API key, no ENGIE data (synthetic fixture).

    python demo_deposits.py              # with the auditor
    python demo_deposits.py --no-audit   # nobody challenges: watch the deposit pay the buyer at settlement

One buyer, one honest seller, one seller that lies about its battery, one auditor. Prints each stage with the
real server functions and the real numbers from the database.
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ["GRIDPACT_DATA_DIR"] = str(ROOT / "fixtures" / "synthetic")      # force the made-up data, whatever .env says
os.environ["GRIDPACT_DB"] = str(Path(tempfile.mkdtemp()) / "demo.db")
sys.path.insert(0, str(ROOT))
from gridpact import data, db, ledger, server, settle   # noqa: E402

LO, HI, PRICE, PENALTY = 68, 79, 45.0, 60.0                                  # 17:00-19:45, $/MWh


def show(title):
    print(f"\n\033[1m{title}\033[0m")


def table():
    c = server.conn_()
    print(f"  {'agent':<8}{'role':<9}{'balance $':>11}{'deposit locked $':>18}{'reputation':>12}{'cap kWh/step':>14}")
    for r in c.execute("SELECT * FROM agents ORDER BY agent_id"):
        print(f"  {r['agent_id']:<8}{r['role']:<9}{r['balance_usd']:>11.2f}{r['stake_locked_usd']:>18.2f}{r['reputation']:>12.2f}{r['trade_cap_kwh']:>14.0f}")


db.reset()
show("1. Everyone registers. The liar's battery is really 2,500 kW but it declares 5,000 kW.")
buyer = server.register_agent("COM_09", "buyer")
honest = server.register_agent("PVB_17", "seller")
liar = server.register_agent("PVB_37", "seller", declared_flex_kw=5000.0)
auditor = server.register_agent("AUD_1", "auditor")
print("  public spec sheet (nameplate): PVB_17 = 5,000 kW, PVB_37 = 2,500 kW")
table()

show("2. The buyer asks both sellers for as much as their caps allow. Each seller accepts and its DEPOSIT is locked.")
for name, s in (("PVB_17", honest), ("PVB_37", liar)):
    kwh = 500.0 if name == "PVB_17" else s["trade_cap_kwh"]
    o = server.propose(buyer["token"], name, LO, HI, kwh, PRICE, PENALTY)
    server.respond(s["token"], o["offer_id"], "accept")
    print(f"  {name} commits {kwh:.0f} kWh/step for 12 steps; deposit = ${PENALTY:.0f}/MWh x {kwh * 12 / 1000:.1f} MWh")
table()
liar_commit = [dict(c) for c in server.conn_().execute("SELECT * FROM commitments WHERE seller = 'PVB_37'")][0]

if "--no-audit" in sys.argv:
    show("3. Nobody challenges. The liar keeps its full promise, 1,250 kWh/step, though its battery can only do 625.")
else:
    show("3. The auditor compares each claim with the public spec sheet and challenges the liar BEFORE settlement.")
    v = server.challenge(auditor["token"], liar_commit["commitment_id"], "envelope exceeds nameplate",
                         "declared 5000 kW vs 2500 kW battery")
    print(f"  verdict: {v['verdict']}  | bounty ${v['bounty_usd']:.2f} moves from the liar's deposit to the auditor")
    print("  the liar's promise is cut to what its real battery can do, and the deposit locked on the cut part is released")
    table()
    t = server.conn_().execute("SELECT kwh_per_step, trimmed_from_kwh FROM commitments WHERE seller='PVB_37'").fetchone()
    print(f"  PVB_37 commitment: {t['trimmed_from_kwh']:.0f} -> {t['kwh_per_step']:.0f} kWh/step")

show("4. Settlement (plain code, no LLM): delivered = what the battery can really add; any shortfall is paid from the deposit.")
conn = server.conn_()
settle.settle_day(conn, data.load_day(agent_ids=("COM_09", "PVB_17", "PVB_37")))
for r in conn.execute("SELECT c.seller, SUM(s.committed_kwh) com, SUM(s.delivered_kwh) dlv, SUM(s.penalty_usd) pen "
                      "FROM settlements s JOIN commitments c USING (commitment_id) GROUP BY c.seller"):
    print(f"  {r['seller']}: committed {r['com']:.0f} kWh, delivered {r['dlv']:.0f} kWh, penalty from deposit ${r['pen']:.2f}")
table()

show("5. The ledger is hash-chained, so any edit would break it.")
print(f"  entries: {conn.execute('SELECT COUNT(*) FROM ledger').fetchone()[0]}   chain intact: {ledger.verify_chain(conn) is None}")
if "--no-audit" in sys.argv:
    print("\nThe deposit covered the buyer, but the promise was never cut and the liar's reputation is untouched.")
else:
    print("\nRun with --no-audit to see the same liar pay from its deposit at settlement instead.")
