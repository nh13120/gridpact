"""HW9: nothing is pushed to agents, so a cut commitment is announced on the affected agent's next successful call, once.
Run 2 of the cold-start test failed because a buyer never looked again; with notices it would have been told on any call.
Pure database tests, no data files, no API key."""
import pytest

from gridpact import db, server

LO, HI = 68, 79


@pytest.fixture
def srv(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(server, "_conn", db.connect(tmp_path / "t.db"))
    c = server.conn_()
    for aid, role, tok, kw, flex, cap in (("COM_09", "buyer", "tb", 0.0, 8000.0, 2000), ("PVB_37", "seller", "tl", 2500.0, 5000.0, 1250),
                                          ("PVB_17", "seller", "th", 5000.0, 5000.0, 1250), ("AUD_1", "auditor", "ta", None, 0.0, 0)):
        c.execute("INSERT INTO agents (agent_id, role, token, bess_power_kw, bess_energy_kwh, declared_flex_kw, trade_cap_kwh) "
                  "VALUES (?,?,?,?,?,?,?)", (aid, role, tok, kw, (kw or 0) * 3, flex, cap))
    c.commit()
    for seller, tok, kwh in (("PVB_37", "tl", 1250.0), ("PVB_17", "th", 250.0)):
        o = server.propose("tb", seller, LO, HI, kwh, 50.0, 60.0)
        assert server.respond(tok, o["offer_id"], "accept")["ok"]
    yield server
    server._conn.close()


def test_no_notices_field_when_nothing_happened(srv):
    assert "notices" not in srv.find_counterparties("tb") and "notices" not in srv.get_inbox("tb")


def test_buyer_and_liar_are_told_once_on_their_next_call(srv):
    assert srv.challenge("ta", 1, "envelope exceeds nameplate", "5000 vs 2500")["verdict"] == "valid"
    r = srv.find_counterparties("tb")                      # any call, not only the one that "should" be polled
    assert len(r["notices"]) == 1 and "cut from 1250 to 625" in r["notices"][0] and "get_commitments" in r["notices"][0]
    assert "notices" not in srv.find_counterparties("tb")                # delivered once
    assert "cut from 1250 to 625" in srv.get_inbox("tl")["notices"][0]   # the seller whose commitment was cut hears too
    assert "notices" not in srv.get_inbox("th")                          # the honest seller does not


def test_a_refused_call_does_not_swallow_the_notice(srv):
    srv.challenge("ta", 1, "envelope exceeds nameplate", "5000 vs 2500")
    assert srv.propose("tb", "PVB_99", LO, HI, 100.0, 50.0, 60.0)["ok"] is False
    assert len(srv.get_commitments("tb")["notices"]) == 1
