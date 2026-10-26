"""Append-only, hash-chained log of every state change.

Each entry stores the hash of the previous entry, and its own hash covers
(prev_hash + its canonical content). Change any byte of any past entry and
`verify_chain` reports where the chain breaks. Nothing here updates or deletes.
"""
import hashlib
import json
from datetime import datetime, timezone

GENESIS = "0" * 64  # prev_hash of the first entry


def canonical(obj):
    """Deterministic JSON: sorted keys, no spaces. Same data -> same bytes -> same hash."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def entry_hash(prev_hash, seq, ts, agent_id, action, payload_json):
    body = canonical({"seq": seq, "ts": ts, "agent_id": agent_id,
                      "action": action, "payload": json.loads(payload_json)})
    return hashlib.sha256((prev_hash + body).encode()).hexdigest()


def append(conn, agent_id, action, payload):
    """Add one entry and return it as a dict. `payload` is any JSON-serialisable dict."""
    last = conn.execute("SELECT seq, hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
    seq = (last["seq"] + 1) if last else 1
    prev_hash = last["hash"] if last else GENESIS
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload_json = canonical(payload)
    h = entry_hash(prev_hash, seq, ts, agent_id, action, payload_json)
    conn.execute("INSERT INTO ledger VALUES (?,?,?,?,?,?,?)",
                 (seq, ts, agent_id, action, payload_json, prev_hash, h))
    return {"seq": seq, "ts": ts, "agent_id": agent_id, "action": action,
            "payload": payload, "prev_hash": prev_hash, "hash": h}


def entries(conn, since_seq=0):
    """All entries with seq > since_seq, oldest first, payload decoded."""
    rows = conn.execute("SELECT * FROM ledger WHERE seq > ? ORDER BY seq", (since_seq,)).fetchall()
    return [{**dict(r), "payload": json.loads(r["payload_json"])} for r in rows]


def verify_chain(conn):
    """Return None if the chain is intact, else the seq of the first bad entry."""
    prev_hash = GENESIS
    for r in conn.execute("SELECT * FROM ledger ORDER BY seq"):
        expected = entry_hash(prev_hash, r["seq"], r["ts"], r["agent_id"], r["action"], r["payload_json"])
        if r["prev_hash"] != prev_hash or r["hash"] != expected:
            return r["seq"]
        prev_hash = r["hash"]
    return None
