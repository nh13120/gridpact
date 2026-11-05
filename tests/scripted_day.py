"""One GridPact day with no LLM, on the synthetic fixture: register, trade, challenge, settle.

    GRIDPACT_DATA_DIR=fixtures/synthetic GRIDPACT_DB=/tmp/day.db python -m tests.scripted_day [--repeat-propose [--request-id]]

Prints one JSON line. --repeat-propose sends the buyer's proposal to PVB_17 twice (a retried request)
and accepts the result both times, to show what the protocol does with a duplicate. With --request-id
both sends carry the same request_id. Used by tests/test_fixture_day.py
and as the reference behaviour for the Nanda Town bridge.
"""
import json
import sys

from gridpact import data, db, ledger, server, settle
from gridpact.config import STEP_H

LO, HI = 68, 79


def main(repeat=False, with_id=False):
    db.reset()
    buyer = server.register_agent("COM_09", "buyer")
    honest = server.register_agent("PVB_17", "seller")
    liar = server.register_agent("PVB_37", "seller", declared_flex_kw=5000.0)   # real battery: 2500 kW
    auditor = server.register_agent("AUD_1", "auditor")
    assert all(x["ok"] for x in (buyer, honest, liar, auditor))
    commits = {}
    for seller, tok, cap in (("PVB_17", honest["token"], honest["trade_cap_kwh"]),
                             ("PVB_37", liar["token"], liar["trade_cap_kwh"])):
        kwh = cap if seller == "PVB_37" else 500
        sends = 2 if (repeat and seller == "PVB_17") else 1
        for _ in range(sends):
            o = server.propose(buyer["token"], seller, LO, HI, kwh, 45.0, 60.0,
                               request_id=f"req-{seller}" if with_id else None)
            assert o["ok"], o
            r = server.respond(tok, o["offer_id"], "accept")
            if r["ok"]:
                commits.setdefault(seller, []).append(r)
    ch = [dict(c) for c in server.conn_().execute("SELECT * FROM commitments WHERE seller = 'PVB_37'")]
    verdict = server.challenge(auditor["token"], ch[0]["commitment_id"], "envelope exceeds nameplate",
                               "declared 5000 kW vs 2500 kW battery")
    day = data.load_day(agent_ids=("COM_09", "PVB_17", "PVB_37"))
    conn = db.connect()
    settle.settle_day(conn, day)
    conn.commit()
    s = {r["commitment_id"]: dict(r) for r in conn.execute("SELECT * FROM commitments")}
    rows = conn.execute("SELECT c.seller, SUM(s.committed_kwh) com, SUM(s.delivered_kwh) dlv, "
                        "SUM(s.penalty_usd) pen FROM settlements s JOIN commitments c USING (commitment_id) "
                        "GROUP BY c.seller").fetchall()
    out = {"commitments": {k: len(v) for k, v in commits.items()},
           "challenge_valid": verdict.get("verdict") == "valid",
           "settled": {r["seller"]: {"committed": r["com"], "delivered": r["dlv"], "penalty": round(r["pen"], 2)} for r in rows},
           "ledger_ok": ledger.verify_chain(conn) is None}
    print(json.dumps(out))


if __name__ == "__main__":
    main("--repeat-propose" in sys.argv, "--request-id" in sys.argv)
