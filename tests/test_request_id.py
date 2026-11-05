"""propose(request_id=...) is idempotent. Pure database tests, no data files, no API key."""
import sqlite3

import pytest

from gridpact import db, server


@pytest.fixture
def srv(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(server, "_conn", db.connect(tmp_path / "t.db"))
    c = server.conn_()
    for aid, role, tok in (("B1", "buyer", "tb"), ("S1", "seller", "ts")):
        c.execute("INSERT INTO agents (agent_id, role, token, bess_power_kw, bess_energy_kwh, declared_flex_kw, "
                  "trade_cap_kwh) VALUES (?,?,?,?,?,?,?)", (aid, role, tok, 4000.0, 12000.0, 4000.0, 1000))
    c.commit()
    yield server
    server._conn.close()


def propose(srv, **kw):
    args = dict(token="tb", to="S1", step_from=68, step_to=79, kwh_per_step=400, price_usd_mwh=45,
                penalty_usd_mwh=60, request_id="r1")
    args.update(kw)
    return srv.propose(**args)


def n_offers(srv):
    return srv.conn_().execute("SELECT COUNT(*) FROM offers").fetchone()[0]


def test_same_request_returns_the_same_offer(srv):
    a, b = propose(srv), propose(srv)
    assert a["ok"] and b["ok"] and b["offer_id"] == a["offer_id"] and b["duplicate"] is True
    assert n_offers(srv) == 1


def test_duplicate_adds_nothing_to_the_ledger(srv):
    propose(srv)
    before = srv.conn_().execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    propose(srv)
    assert srv.conn_().execute("SELECT COUNT(*) FROM ledger").fetchone()[0] == before


def test_duplicate_after_acceptance_reports_status_and_stays_one_commitment(srv):
    a = propose(srv)
    srv.respond("ts", a["offer_id"], "accept")
    b = propose(srv)
    assert b["ok"] and b["offer_id"] == a["offer_id"] and b["status"] == "accepted"
    assert srv.conn_().execute("SELECT COUNT(*) FROM commitments").fetchone()[0] == 1


def test_same_id_with_different_terms_is_refused(srv):
    propose(srv)
    r = propose(srv, price_usd_mwh=50)
    assert not r["ok"] and "different terms" in r["reason"]
    assert n_offers(srv) == 1


def test_without_request_id_nothing_is_deduplicated(srv):
    assert propose(srv, request_id=None)["offer_id"] != propose(srv, request_id=None)["offer_id"]


def test_request_ids_are_per_sender(srv):
    srv.conn_().execute("INSERT INTO agents (agent_id, role, token, bess_power_kw, bess_energy_kwh, declared_flex_kw, "
                        "trade_cap_kwh) VALUES ('B2','buyer','tb2',0,0,0,0)")
    srv.conn_().commit()
    assert propose(srv)["offer_id"] != propose(srv, token="tb2")["offer_id"]


def test_bad_request_id_is_refused(srv):
    assert not propose(srv, request_id="")["ok"]
    assert not propose(srv, request_id="x" * 129)["ok"]


def test_old_database_is_migrated(tmp_path):
    p = tmp_path / "old.db"
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE offers (offer_id INTEGER PRIMARY KEY, from_agent TEXT NOT NULL, to_agent TEXT NOT NULL, "
              "step_from INTEGER NOT NULL, step_to INTEGER NOT NULL, kwh_per_step REAL NOT NULL, price_usd_mwh REAL NOT NULL, "
              "penalty_usd_mwh REAL NOT NULL, status TEXT NOT NULL DEFAULT 'open', round_opened INTEGER NOT NULL DEFAULT 0)")
    c.commit(); c.close()
    conn = db.connect(p)
    assert "request_id" in {r[1] for r in conn.execute("PRAGMA table_info(offers)")}
