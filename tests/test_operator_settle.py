"""Incremental settlement and the operator tool (HW8). No data files in the unit tests."""
import pandas as pd
import pytest

from gridpact import db, settle
from tests.test_settle import add_agent, make_day


def seller(conn, power=1000.0, energy=10000.0):
    add_agent(conn, "S1", "seller", declared=power, power=power, energy=energy)
    add_agent(conn, "B1", "buyer")


def commit(conn, kwh, steps=(68, 69), penalty=60.0, price=40.0):
    conn.execute("INSERT INTO offers (from_agent, to_agent, step_from, step_to, kwh_per_step, price_usd_mwh, penalty_usd_mwh) "
                 "VALUES ('B1','S1',?,?,?,?,?)", (steps[0], steps[1], kwh, price, penalty))
    oid = conn.execute("SELECT MAX(offer_id) FROM offers").fetchone()[0]
    stake = penalty * kwh * (steps[1] - steps[0] + 1) / 1000
    conn.execute("INSERT INTO commitments (offer_id, seller, buyer, step_from, step_to, kwh_per_step, price_usd_mwh, "
                 "penalty_usd_mwh, stake_usd) VALUES (?,?,?,?,?,?,?,?,?)", (oid, "S1", "B1", *steps, kwh, price, penalty, stake))
    conn.execute("UPDATE agents SET stake_locked_usd = stake_locked_usd + ? WHERE agent_id = 'S1'", (stake,))
    conn.commit()


def totals(conn):
    return [tuple(r) for r in conn.execute("SELECT commitment_id, step, delivered_kwh, shortfall_kwh, penalty_usd "
                                           "FROM settlements ORDER BY commitment_id, step")]


def test_incremental_twice_equals_one_call(tmp_path):
    a, b = db.connect(tmp_path / "a.db"), db.connect(tmp_path / "b.db")
    for conn in (a, b):
        seller(conn)
    commit(a, 200); commit(a, 150)                      # both land before the single settlement
    settle.settle_day(a, make_day())
    commit(b, 200); settle.settle_day(b, make_day(), incremental=True)
    commit(b, 150); settle.settle_day(b, make_day(), incremental=True)   # second trade settled later
    assert totals(a) == totals(b)


def test_incremental_does_not_resettle(tmp_path):
    conn = db.connect(tmp_path / "t.db"); seller(conn); commit(conn, 200)
    assert len(settle.settle_day(conn, make_day(), incremental=True)) == 2
    assert settle.settle_day(conn, make_day(), incremental=True) == []
    assert conn.execute("SELECT COUNT(*) FROM settlements").fetchone()[0] == 2


def test_shared_battery_across_later_trade(tmp_path):
    """Power for a step is 250 kWh (1000 kW x 0.25 h). 200 settled first leaves 50 for the next trade."""
    conn = db.connect(tmp_path / "t.db"); seller(conn)
    commit(conn, 200); settle.settle_day(conn, make_day(), incremental=True)
    commit(conn, 150); settle.settle_day(conn, make_day(), incremental=True)
    second = [r for r in totals(conn) if r[0] == 2]
    assert all(r[2] == 50.0 and r[3] == 100.0 for r in second)


def test_operator_tool_is_off_without_a_key(tmp_path, monkeypatch):
    from gridpact import server
    monkeypatch.delenv("GRIDPACT_OPERATOR_KEY", raising=False)
    assert server.operator_settle("anything") == {"ok": False, "reason": "operator tools are disabled on this server"}
    monkeypatch.setenv("GRIDPACT_OPERATOR_KEY", "right")
    assert server.operator_settle("wrong")["reason"] == "wrong operator key"
