"""Unsupported or out-of-limit requests are refused with a reason and change nothing (HW9 boundary cases).
The cold-start buyer's request to PVB_99 was refused as 'not registered' before the step range was ever checked, so the
range and the other limits are exercised here directly. Pure database tests, no data files, no API key."""
import pytest

from gridpact import db, server


@pytest.fixture
def srv(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(server, "_conn", db.connect(tmp_path / "t.db"))
    c = server.conn_()
    for aid, role, tok, kw, flex, cap in (("COM_09", "buyer", "tb", 0.0, 8000.0, 2000), ("PVB_17", "seller", "ts", 5000.0, 5000.0, 1250),
                                          ("PVB_37", "seller", "tl", 2500.0, 5000.0, 1250), ("AUD_1", "auditor", "ta", None, 0.0, 0)):
        c.execute("INSERT INTO agents (agent_id, role, token, bess_power_kw, bess_energy_kwh, declared_flex_kw, trade_cap_kwh) "
                  "VALUES (?,?,?,?,?,?,?)", (aid, role, tok, kw, (kw or 0) * 3, flex, cap))
    c.commit()
    yield server
    server._conn.close()


def counts(srv):
    c = srv.conn_()
    return tuple(c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("offers", "commitments", "ledger"))


@pytest.mark.parametrize("args, why", [
    (dict(to="PVB_99", step_from=68, step_to=79), "not registered"),
    (dict(to="PVB_17", step_from=100, step_to=110), "steps must satisfy"),
    (dict(to="PVB_17", step_from=79, step_to=68), "steps must satisfy"),
    (dict(to="PVB_17", step_from=68, step_to=79, kwh_per_step=5000), "can commit at most"),
    (dict(to="PVB_17", step_from=68, step_to=79, price_usd_mwh=-5), "must be finite"),
    (dict(to="PVB_17", step_from=68, step_to=79, request_id=""), "request_id"),
    (dict(to="COM_09", step_from=68, step_to=79), "exactly one buyer and one seller"),
])
def test_unsupported_proposals_are_refused_and_change_nothing(srv, args, why):
    before = counts(srv)
    call = dict(token="tb", kwh_per_step=100.0, price_usd_mwh=50.0, penalty_usd_mwh=60.0)
    call.update(args)
    r = srv.propose(**call)
    assert r["ok"] is False and why in r["reason"] and counts(srv) == before


def test_wrong_token_and_wrong_role_are_refused(srv):
    assert srv.propose("nope", "PVB_17", 68, 79, 100.0, 50.0, 60.0) == {"ok": False, "reason": "unknown token"}
    assert srv.challenge("tb", 1, "x", "y")["ok"] is False                      # buyers cannot challenge
    assert srv.find_counterparties("ta")["ok"] is False                         # auditors cannot trade


def test_a_second_valid_challenge_on_one_commitment_is_not_paid_twice(srv):
    o = srv.propose("tb", "PVB_37", 68, 79, 1250.0, 50.0, 60.0)
    srv.respond("tl", o["offer_id"], "accept")
    assert srv.challenge("ta", 1, "envelope exceeds nameplate", "5000 vs 2500")["verdict"] == "valid"
    again = srv.challenge("ta", 1, "envelope exceeds nameplate", "5000 vs 2500")
    assert again["verdict"] == "duplicate"
