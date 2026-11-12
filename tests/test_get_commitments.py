"""Regression for the HW9 cold-start finding: a buyer could not see that its commitment had been cut by a valid
challenge (get_inbox shows only offer status). get_commitments shows the current volume and the original one.
Pure database tests, no data files, no API key."""
import pytest

from gridpact import db, server

LO, HI = 68, 79


@pytest.fixture
def srv(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(server, "_conn", db.connect(tmp_path / "t.db"))
    c = server.conn_()
    rows = (("COM_09", "buyer", "tb", 0.0, 0.0, 8000.0, 2000),
            ("PVB_37", "seller", "tl", 2500.0, 7500.0, 5000.0, 1250),     # real battery 2500 kW, declares 5000
            ("PVB_17", "seller", "th", 5000.0, 15000.0, 5000.0, 1250),
            ("AUD_1", "auditor", "ta", None, None, 0.0, 0))
    for aid, role, tok, kw, kwh, flex, cap in rows:
        c.execute("INSERT INTO agents (agent_id, role, token, bess_power_kw, bess_energy_kwh, declared_flex_kw, "
                  "trade_cap_kwh) VALUES (?,?,?,?,?,?,?)", (aid, role, tok, kw, kwh, flex, cap))
    c.commit()
    for seller, tok, kwh in (("PVB_37", "tl", 1250.0), ("PVB_17", "th", 250.0)):
        o = server.propose("tb", seller, LO, HI, kwh, 50.0, 60.0)
        assert server.respond(tok, o["offer_id"], "accept")["ok"]
    yield server
    server._conn.close()


def test_buyer_sees_the_cut_after_a_valid_challenge(srv):
    before = srv.get_commitments("tb")["commitments"]
    assert [c["kwh_per_step"] for c in before] == [1250.0, 250.0] and all(c["trimmed_from_kwh"] is None for c in before)
    assert srv.challenge("ta", 1, "envelope exceeds nameplate", "declared 5000 vs 2500")["verdict"] == "valid"
    after = {c["seller"]: c for c in srv.get_commitments("tb")["commitments"]}
    assert after["PVB_37"]["kwh_per_step"] == 625.0 and after["PVB_37"]["trimmed_from_kwh"] == 1250.0
    assert after["PVB_37"]["status"] == "challenged" and after["PVB_17"]["kwh_per_step"] == 250.0


def test_each_party_sees_only_its_own_and_auditors_see_all(srv):
    assert [c["seller"] for c in srv.get_commitments("th")["commitments"]] == ["PVB_17"]
    assert [c["seller"] for c in srv.get_commitments("tl")["commitments"]] == ["PVB_37"]
    assert len(srv.get_commitments("ta")["commitments"]) == 2
    assert srv.get_commitments("nope") == {"ok": False, "reason": "unknown token"}
