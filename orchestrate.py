"""Run one GridPact day end to end: negotiation rounds -> settlement -> audit -> P&L.

Usage:  python orchestrate.py           (negotiation + settlement + audit on the existing DB state)
        python orchestrate.py --demo    (reset the DB first, then also run verify.py)
"""
import sys

from gridpact import data, db, server
from gridpact.config import GRID_FEE_USD_MWH
from agents.run_agent import run

BUYER, HONEST, LIAR, AUDITOR = "COM_09", "PVB_17", "PVB_37", "AUD_01"
STEP_FROM, STEP_TO = 68, 79   # 17:00-19:45 local
MAX_ROUNDS = 4


def q(sql, *args):
    c = db.connect()
    rows = c.execute(sql, args).fetchall()
    c.close()
    return rows


def token_of(agent_id):
    r = q("SELECT token FROM agents WHERE agent_id = ?", agent_id)
    return r[0]["token"] if r else None


def commitments_with(seller):
    return q("SELECT * FROM commitments WHERE seller = ?", seller)


def main(demo=False):
    if demo:
        db.reset()
    proc = server.launch()
    total_cost = 0.0
    try:
        # --- facts from the data (obs columns only) --------------------------------
        day = data.load_day()
        meta = data.load_metadata()
        window = day[day.step.between(STEP_FROM, STEP_TO)]
        need = window[window.entity_id == BUYER].deficit_kwh.mean()
        da = window.price_da_usd_mwh.mean()
        grid_price = da + GRID_FEE_USD_MWH
        facts = (f"Trading window: steps {STEP_FROM} to {STEP_TO} (17:00-19:45 local, 12 steps). "
                 f"Day-ahead wholesale price {da:.0f} $/MWh; grid import price {grid_price:.0f} $/MWh.")
        print(f"Day {data.DAY}: buyer needs ~{need:.0f} kWh/step; wholesale {da:.0f}, grid {grid_price:.0f} $/MWh")

        # --- owners register their agents -------------------------------------------
        # The owner, not the LLM, declares the envelope: for the liar it is ~2x the real one.
        # (Mirrors ENGIE's malicious dataset, which corrupts what an agent reports.) Each
        # registration goes through the same server code and lands on the ledger.
        print("\n----- registration (by owners) -----")
        for agent_id, role, flex in ((BUYER, "buyer", None),
                                     (HONEST, "seller", None),
                                     (LIAR, "seller", 2 * float(meta.loc[LIAR].flex_up_kw)),
                                     (AUDITOR, "auditor", None)):
            r = server.register_agent(agent_id, role, flex)
            assert r["ok"], r
            print(f"  {agent_id:7s} {role:8s} declared_flex_kw={r['declared_flex_kw']:>8} cap={r['trade_cap_kwh']} kWh/step")
        server._conn.close(); server._conn = None   # hand the DB back to the server process

        # --- day-ahead negotiation ------------------------------------------------
        for rnd in range(1, MAX_ROUNDS + 1):
            server.set_round(rnd)
            print(f"\n----- negotiation round {rnd} -----")
            tok = token_of(BUYER)
            if rnd == 1:
                task = (f"You are {BUYER}, token {tok}. Find counterparties and propose a trade to EVERY seller "
                        f"for the full window, each at its trade cap (kWh per step). You need about {need:.0f} kWh "
                        f"per step in total. {facts}")
            else:
                task = (f"You are {BUYER}, token {tok}. Round {rnd}. Check your inbox: accept counters at or "
                        f"below the grid price, otherwise counter. If a seller rejected and has no commitment "
                        f"with you yet, propose again at a better price. {facts}")
            _, c = run("buyer", "buyer.md", task); total_cost += c

            for seller, role_file in ((HONEST, "honest_seller.md"), (LIAR, "liar.md")):
                if commitments_with(seller):
                    continue
                m = meta.loc[seller]
                tok = token_of(seller)
                envelope = (f"Your declared envelope is {m.flex_up_kw:.0f} kW, which is your true battery power."
                            if role_file == "honest_seller.md" else
                            f"Your owner registered a declared envelope of {2 * m.flex_up_kw:.0f} kW; the real "
                            f"battery is {m.bess_power_kw:.0f} kW.")
                task = (f"You are {seller}, token {tok}. Round {rnd}. {envelope} Check your inbox and answer "
                        f"every open offer. Your minimum price is {da:.0f} $/MWh (wholesale). {facts}")
                _, c = run(seller, role_file, task); total_cost += c

            if commitments_with(HONEST) and commitments_with(LIAR):
                break

        print("\n----- commitments -----")
        for r in q("SELECT * FROM commitments"):
            print(f"  #{r['commitment_id']} {r['seller']} -> {r['buyer']}: {r['kwh_per_step']:.0f} kWh/step "
                  f"x {r['step_to'] - r['step_from'] + 1} steps @ {r['price_usd_mwh']:.0f} $/MWh, "
                  f"penalty {r['penalty_usd_mwh']:.0f}, stake ${r['stake_usd']:.0f}")
        print(f"\nLLM cost so far: ${total_cost:.3f}")
    finally:
        proc.terminate()


if __name__ == "__main__":
    main(demo="--demo" in sys.argv)
