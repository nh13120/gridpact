"""HW9 cold-start finding: an auditor could not learn a seller's real battery size from GridPact alone (the
nameplate was only in a parquet file). get_registry returns it. Pure database tests, no data files, no API key."""
import pytest

from gridpact import db, server


@pytest.fixture
def srv(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(server, "_conn", db.connect(tmp_path / "t.db"))
    c = server.conn_()
    for aid, role, tok, kw, flex in (("COM_09", "buyer", "tb", 0.0, 8000.0), ("PVB_37", "seller", "tl", 2500.0, 5000.0),
                                     ("PVB_17", "seller", "th", 5000.0, 5000.0), ("AUD_1", "auditor", "ta", None, 0.0)):
        c.execute("INSERT INTO agents (agent_id, role, token, bess_power_kw, declared_flex_kw, trade_cap_kwh) "
                  "VALUES (?,?,?,?,?,?)", (aid, role, tok, kw, flex, 0))
    c.commit()
    yield server
    server._conn.close()


def test_auditor_sees_nameplate_next_to_the_declared_figure(srv):
    r = srv.get_registry("ta")
    assert r["ok"]
    by = {a["agent_id"]: a for a in r["agents"]}
    assert by["PVB_37"]["nameplate_kw"] == 2500.0 and by["PVB_37"]["declared_flex_kw"] == 5000.0   # the liar, visible
    assert by["PVB_17"]["nameplate_kw"] == 5000.0 and by["PVB_17"]["declared_flex_kw"] == 5000.0
    assert by["AUD_1"]["nameplate_kw"] is None


def test_any_registered_role_may_read_it_but_a_bad_token_may_not(srv):
    assert srv.get_registry("tb")["ok"] and srv.get_registry("th")["ok"]
    assert srv.get_registry("nope")["ok"] is False


def test_it_gives_facts_not_verdicts_and_no_secrets(srv):
    text = str(srv.get_registry("ta"))
    assert "valid" not in text and "token" not in text and "tl" not in {a["agent_id"] for a in srv.get_registry("ta")["agents"]}
    n = srv.conn_().execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    srv.get_registry("ta")
    assert srv.conn_().execute("SELECT COUNT(*) FROM ledger").fetchone()[0] == n          # a read changes nothing
