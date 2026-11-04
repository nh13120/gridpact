"""Settlement and adjudication tests. No ENGIE data, no API key, no LLM.

A tiny fake world: one buyer, one liar (declares 2x its battery), one honest seller and one auditor.
The liar commits 1217 kWh/step for 12 steps but its battery can only add 608.75 kWh/step.
"""
import pytest
import pandas as pd

from gridpact import db, ledger, settle

STEPS = range(68, 80)            # 17:00-19:45
RT_PRICE = 50.0                  # $/MWh real time
GRID_FEE = 30.0                  # config.GRID_FEE_USD_MWH
PRICE, PENALTY, KWH = 40.0, 70.0, 1217.0


def make_day():
    """What settle_day needs from data.load_day: a `step` and a real-time `price_usd_mwh` column."""
    return pd.DataFrame({"step": list(range(96)), "price_usd_mwh": [RT_PRICE] * 96})


def add_agent(conn, agent_id, role, declared=None, power=None, energy=None):
    conn.execute(
        "INSERT INTO agents (agent_id, role, token, bess_power_kw, bess_energy_kwh, declared_flex_kw, "
        "trade_cap_kwh) VALUES (?,?,?,?,?,?,?)",
        (agent_id, role, "tok_" + agent_id, power, energy, declared, 0))


def world(tmp_path, liar_declared=4870.0):
    conn = db.connect(tmp_path / "t.db")
    add_agent(conn, "BUY", "buyer")
    add_agent(conn, "LIAR", "seller", declared=liar_declared, power=2435.0, energy=8378.0)
    add_agent(conn, "AUD", "auditor")
    stake = PENALTY * KWH * len(STEPS) / 1000
    conn.execute("INSERT INTO offers (offer_id, from_agent, to_agent, step_from, step_to, kwh_per_step, "
                 "price_usd_mwh, penalty_usd_mwh, status) VALUES (1,'BUY','LIAR',68,79,?,?,?,'accepted')",
                 (KWH, PRICE, PENALTY))
    conn.execute("INSERT INTO commitments (commitment_id, offer_id, seller, buyer, step_from, step_to, "
                 "kwh_per_step, price_usd_mwh, penalty_usd_mwh, stake_usd) VALUES (1,1,'LIAR','BUY',68,79,?,?,?,?)",
                 (KWH, PRICE, PENALTY, stake))
    conn.execute("UPDATE agents SET stake_locked_usd = ?, trade_cap_kwh = ? WHERE agent_id = 'LIAR'",
                 (stake, KWH))   # cap = what the owner registered (floor of declared x 0.25)
    conn.commit()
    return conn


def balances(conn):
    return {r["agent_id"]: r["balance_usd"] for r in conn.execute("SELECT agent_id, balance_usd FROM agents")}


def test_shortfall_penalty_and_grid_cost(tmp_path):
    conn = world(tmp_path)
    rows = settle.settle_day(conn, make_day())
    assert len(rows) == 12
    delivered = 2435.0 * 0.25                       # battery power x 15 min
    short = KWH - delivered
    r = rows[0]
    assert r["delivered_kwh"] == pytest.approx(delivered, abs=1e-3)
    assert r["shortfall_kwh"] == pytest.approx(short, abs=1e-3)
    assert r["penalty_usd"] == pytest.approx(short / 1000 * PENALTY, abs=1e-3)
    assert r["grid_usd"] == pytest.approx(short / 1000 * (RT_PRICE + GRID_FEE), abs=1e-3)


def test_settlement_conserves_money(tmp_path):
    conn = world(tmp_path)
    rows = settle.settle_day(conn, make_day())
    # energy and penalties only move between agents; only grid payments leave the system
    assert sum(balances(conn).values()) == pytest.approx(-sum(r["grid_usd"] for r in rows), abs=1e-6)


def test_valid_challenge_pays_bounty_and_conserves_money(tmp_path):
    conn = world(tmp_path)
    rows = settle.settle_day(conn, make_day())
    before = balances(conn)
    verdict = settle.adjudicate(conn, conn.execute("SELECT * FROM commitments").fetchone(), "AUD",
                                "envelope exceeds nameplate", "declared 4870 vs 2435")
    conn.commit()
    after = balances(conn)
    bounty = verdict["bounty_usd"]
    assert verdict["verdict"] == "valid" and bounty > 0
    assert after["AUD"] - before["AUD"] == pytest.approx(bounty, abs=0.01)
    # THE BUG THIS GUARDS: the seller must lose the bounty from its balance, not only from its stake
    assert before["LIAR"] - after["LIAR"] == pytest.approx(bounty, abs=0.01)
    assert sum(after.values()) == pytest.approx(-sum(r["grid_usd"] for r in rows), abs=0.01)
    liar = conn.execute("SELECT reputation, trade_cap_kwh FROM agents WHERE agent_id = 'LIAR'").fetchone()
    assert liar["reputation"] == 0.5 and liar["trade_cap_kwh"] == 608


def test_second_challenge_on_same_commitment_is_duplicate(tmp_path):
    conn = world(tmp_path)
    settle.settle_day(conn, make_day())
    c = conn.execute("SELECT * FROM commitments").fetchone()
    assert settle.adjudicate(conn, c, "AUD", "x", "y")["verdict"] == "valid"
    again = settle.adjudicate(conn, c, "AUD", "x", "y")
    assert again["verdict"] == "duplicate"


def test_challenging_an_honest_seller_costs_the_auditor_a_bond(tmp_path):
    conn = world(tmp_path, liar_declared=2435.0)    # declares exactly its nameplate: honest
    settle.settle_day(conn, make_day())
    before = balances(conn)
    verdict = settle.adjudicate(conn, conn.execute("SELECT * FROM commitments").fetchone(), "AUD", "x", "y")
    after = balances(conn)
    assert verdict["verdict"] == "invalid"
    assert before["AUD"] - after["AUD"] == pytest.approx(settle.CHALLENGE_BOND_USD)
    assert after["LIAR"] == before["LIAR"]


def test_valid_challenge_before_settlement_trims_commitment_to_real_cap(tmp_path):
    """v2: challenged BEFORE settlement -> the commitment is cut to the real cap, the stake on the cut part is
    released, and settlement then has no shortfall. (Challenged after settlement -> nothing is trimmed.)"""
    conn = world(tmp_path)
    c = conn.execute("SELECT * FROM commitments").fetchone()
    settle.adjudicate(conn, c, "AUD", "x", "y")
    conn.commit()
    c2 = conn.execute("SELECT * FROM commitments").fetchone()
    assert c2["kwh_per_step"] == 608 and c2["trimmed_from_kwh"] == KWH
    assert c2["stake_usd"] == pytest.approx(PENALTY * 608 * 12 / 1000)
    liar = conn.execute("SELECT stake_locked_usd FROM agents WHERE agent_id = 'LIAR'").fetchone()
    assert liar["stake_locked_usd"] == pytest.approx(c2["stake_usd"] - 0.10 * PENALTY * KWH * 12 / 1000, abs=0.01)
    rows = settle.settle_day(conn, make_day())
    assert sum(r["shortfall_kwh"] for r in rows) == 0
    assert conn.execute("SELECT COUNT(*) FROM ledger WHERE action = 'trim'").fetchone()[0] == 1


def test_ledger_chain_is_intact_after_settlement_and_challenge(tmp_path):
    conn = world(tmp_path)
    settle.settle_day(conn, make_day())
    settle.adjudicate(conn, conn.execute("SELECT * FROM commitments").fetchone(), "AUD", "x", "y")
    conn.commit()
    assert ledger.verify_chain(conn) is None
    assert conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0] == 12 + 1   # 12 settle + 1 challenge
