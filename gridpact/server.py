"""GridPact MCP server: the 7 tools agents call.

Every tool returns a plain dict. Success looks like {"ok": true, ...}; a refused
call looks like {"ok": false, "reason": "..."} so an LLM agent can read why.
Rules live here, not in prompts: an agent can only act as itself (token),
can only commit up to its declared envelope / cap, and stake is locked when a
commitment is created.

Run it:  python -m gridpact.server        (streamable HTTP on config.PORT)
"""
import math
import secrets
import socket
import threading
import subprocess
import sys
import time

from mcp.server import MCPServer

from gridpact import data, db, ledger
from gridpact.config import N_STEPS, OFFER_TTL_ROUNDS, PORT, ROOT, STEP_H

mcp = MCPServer("gridpact")
_conn = None
# ponytail: one global lock around every write tool. MCP runs tools in worker threads, so
# without it two accepts could both pass the cap check. Per-seller locks if throughput matters.
_write = threading.Lock()


def _finite(*xs):
    """True if every value is a real, finite number (NaN and inf would slip past < > checks)."""
    return all(isinstance(x, (int, float)) and math.isfinite(x) for x in xs)


def conn_():
    """One connection, opened on first use (so db.reset() before the first call is safe)."""
    global _conn
    if _conn is None:
        _conn = db.connect()
    return _conn


# --- helpers -----------------------------------------------------------------

def _agent(token):
    return conn_().execute("SELECT * FROM agents WHERE token = ?", (token,)).fetchone()


def _agent_by_id(agent_id):
    return conn_().execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()


def _public(row):
    """What other agents may see about an agent (never the token)."""
    d = {k: row[k] for k in ("agent_id", "role", "bus", "declared_flex_kw",
                             "flex_duration_h", "reputation", "trade_cap_kwh")}
    return {k: (round(v, 1) if isinstance(v, float) else v) for k, v in d.items()}


def _round():
    r = conn_().execute("SELECT value FROM kv WHERE key = 'round'").fetchone()
    return int(r["value"]) if r else 0


def _committed_kwh(seller, step_from, step_to):
    """Largest per-step kWh this seller has already committed inside the window."""
    rows = conn_().execute(
        "SELECT kwh_per_step FROM commitments WHERE seller = ? AND status IN ('active', 'challenged') "
        "AND NOT (step_to < ? OR step_from > ?)", (seller, step_from, step_to)).fetchall()
    return sum(r["kwh_per_step"] for r in rows)


def _log(agent_id, action, payload):
    entry = ledger.append(conn_(), agent_id, action, payload)
    conn_().commit()
    return entry["seq"]


# --- tools -------------------------------------------------------------------

@mcp.tool()
def register_agent(agent_id: str, role: str, declared_flex_kw: float | None = None) -> dict:
    """Join GridPact as an ENGIE agent. role is buyer, seller or auditor.
    Sellers may declare the flexibility (kW) they can deliver on top of their baseline;
    default is the envelope from the public registry. Returns a secret token: pass it
    to every other tool. Only the agent that owns an ID may act for it."""
    if role not in ("buyer", "seller", "auditor"):
        return {"ok": False, "reason": "role must be buyer, seller or auditor"}
    if _agent_by_id(agent_id):
        return {"ok": False, "reason": f"{agent_id} is already registered"}
    meta = data.load_metadata((agent_id,))   # any entity in the ENGIE registry may register
    m = meta.loc[agent_id] if len(meta) else None
    if role != "auditor" and m is None:
        return {"ok": False, "reason": f"{agent_id} is not in the ENGIE registry"}
    if declared_flex_kw is not None and not (_finite(declared_flex_kw) and declared_flex_kw > 0):
        return {"ok": False, "reason": "declared_flex_kw must be a finite number > 0"}
    if m is not None and role != {"community": "buyer", "pv_bess": "seller"}[m.entity_type]:
        return {"ok": False, "reason": f"{agent_id} is a {m.entity_type}; it must register as the matching role"}
    flex = float(declared_flex_kw) if declared_flex_kw is not None else (float(m.flex_up_kw) if m is not None else 0.0)
    cap = math.floor(flex * STEP_H)  # whole kWh per step the agent may commit (floor: no 1363.66 caps)
    token = secrets.token_hex(8)
    conn_().execute(
        "INSERT INTO agents (agent_id, role, token, bus, bess_power_kw, bess_energy_kwh, "
        "declared_flex_kw, flex_duration_h, trade_cap_kwh) VALUES (?,?,?,?,?,?,?,?,?)",
        (agent_id, role, token,
         int(m.bus) if m is not None else None,
         float(m.bess_power_kw) if m is not None else None,
         float(m.bess_energy_kwh) if m is not None else None,
         flex, float(m.flex_duration_h) if m is not None else None, cap))
    row = _agent_by_id(agent_id)
    seq = _log(agent_id, "register", _public(row))
    return {"ok": True, "token": token, "ledger_seq": seq, **_public(row)}


@mcp.tool()
def find_counterparties(token: str) -> dict:
    """List agents you could trade with (buyers see sellers, sellers see buyers),
    with their reputation (1.0 = clean) and trade cap in kWh per 15-min step."""
    me = _agent(token)
    if not me:
        return {"ok": False, "reason": "unknown token; call register_agent first"}
    # ponytail: no area filter; all demo agents were picked to be neighbours (DATA_NOTES.md).
    # Add a bus-distance filter when the agent set grows.
    want = {"buyer": "seller", "seller": "buyer"}.get(me["role"])
    if not want:
        return {"ok": False, "reason": "auditors do not trade"}
    rows = conn_().execute("SELECT * FROM agents WHERE role = ?", (want,)).fetchall()
    return {"ok": True, "round": _round(), "counterparties": [_public(r) for r in rows]}


@mcp.tool()
def propose(token: str, to: str, step_from: int, step_to: int, kwh_per_step: float,
            price_usd_mwh: float, penalty_usd_mwh: float) -> dict:
    """Offer a trade: `kwh_per_step` delivered in every 15-min step from step_from to
    step_to (inclusive, 0..95, step 68 = 17:00 local) at `price_usd_mwh`. The seller
    pays `penalty_usd_mwh` per MWh it fails to deliver, from a stake locked at acceptance.
    The seller side (you or `to`) must have the cap for it."""
    me = _agent(token)
    if not me:
        return {"ok": False, "reason": "unknown token"}
    other = _agent_by_id(to)
    if not other:
        return {"ok": False, "reason": f"{to} is not registered"}
    if {me["role"], other["role"]} != {"buyer", "seller"}:
        return {"ok": False, "reason": "a trade needs exactly one buyer and one seller"}
    if not (0 <= step_from <= step_to < N_STEPS):
        return {"ok": False, "reason": f"steps must satisfy 0 <= step_from <= step_to < {N_STEPS}"}
    if not _finite(kwh_per_step, price_usd_mwh, penalty_usd_mwh) or kwh_per_step <= 0 or price_usd_mwh <= 0 or penalty_usd_mwh < 0:
        return {"ok": False, "reason": "kwh_per_step and price must be finite and > 0, penalty finite and >= 0"}
    seller = me if me["role"] == "seller" else other
    with _write:
        return _propose_locked(me, seller, to, step_from, step_to, kwh_per_step, price_usd_mwh, penalty_usd_mwh)


def _propose_locked(me, seller, to, step_from, step_to, kwh_per_step, price_usd_mwh, penalty_usd_mwh):
    room = seller["trade_cap_kwh"] - _committed_kwh(seller["agent_id"], step_from, step_to)
    if kwh_per_step > room + 1e-9:
        return {"ok": False, "reason": f"{seller['agent_id']} can commit at most {math.floor(room)} kWh/step in that window"}
    cur = conn_().execute(
        "INSERT INTO offers (from_agent, to_agent, step_from, step_to, kwh_per_step, "
        "price_usd_mwh, penalty_usd_mwh, round_opened) VALUES (?,?,?,?,?,?,?,?)",
        (me["agent_id"], to, step_from, step_to, kwh_per_step, price_usd_mwh, penalty_usd_mwh, _round()))
    offer_id = cur.lastrowid
    payload = {"offer_id": offer_id, "to": to, "step_from": step_from, "step_to": step_to,
               "kwh_per_step": kwh_per_step, "price_usd_mwh": price_usd_mwh, "penalty_usd_mwh": penalty_usd_mwh}
    seq = _log(me["agent_id"], "propose", payload)
    return {"ok": True, "offer_id": offer_id, "ledger_seq": seq}


@mcp.tool()
def respond(token: str, offer_id: int, action: str, counter_price_usd_mwh: float | None = None) -> dict:
    """Answer an offer addressed to you. action = accept | reject | counter.
    accept creates a commitment and locks the seller's stake (penalty x total kWh).
    counter rejects the offer and opens a new one back at `counter_price_usd_mwh`."""
    me = _agent(token)
    if not me:
        return {"ok": False, "reason": "unknown token"}
    offer = conn_().execute("SELECT * FROM offers WHERE offer_id = ?", (offer_id,)).fetchone()
    if not offer or offer["to_agent"] != me["agent_id"]:
        return {"ok": False, "reason": "no such offer addressed to you"}
    if offer["status"] != "open":
        return {"ok": False, "reason": f"offer is {offer['status']}"}
    if action not in ("accept", "reject", "counter"):
        return {"ok": False, "reason": "action must be accept, reject or counter"}
    if counter_price_usd_mwh is not None and not _finite(counter_price_usd_mwh):
        return {"ok": False, "reason": "counter_price_usd_mwh must be a finite number"}
    with _write:
        return _respond_locked(me, offer_id, action, counter_price_usd_mwh)


def _respond_locked(me, offer_id, action, counter_price_usd_mwh):
    # Re-read under the lock: another thread may have answered this offer meanwhile.
    offer = conn_().execute("SELECT * FROM offers WHERE offer_id = ?", (offer_id,)).fetchone()
    if offer["status"] != "open":
        return {"ok": False, "reason": f"offer is {offer['status']}"}
    if action == "reject":
        conn_().execute("UPDATE offers SET status = 'rejected' WHERE offer_id = ?", (offer_id,))
        return {"ok": True, "ledger_seq": _log(me["agent_id"], "reject", {"offer_id": offer_id})}

    if action == "counter":
        if not counter_price_usd_mwh or counter_price_usd_mwh <= 0:
            return {"ok": False, "reason": "counter needs counter_price_usd_mwh > 0"}
        conn_().execute("UPDATE offers SET status = 'rejected' WHERE offer_id = ?", (offer_id,))
        cur = conn_().execute(
            "INSERT INTO offers (from_agent, to_agent, step_from, step_to, kwh_per_step, "
            "price_usd_mwh, penalty_usd_mwh, round_opened) VALUES (?,?,?,?,?,?,?,?)",
            (me["agent_id"], offer["from_agent"], offer["step_from"], offer["step_to"],
             offer["kwh_per_step"], counter_price_usd_mwh, offer["penalty_usd_mwh"], _round()))
        new_id = cur.lastrowid
        seq = _log(me["agent_id"], "counter", {"offer_id": offer_id, "new_offer_id": new_id,
                                               "price_usd_mwh": counter_price_usd_mwh})
        return {"ok": True, "new_offer_id": new_id, "ledger_seq": seq}

    # accept: re-check the seller's room (another deal may have landed since), then commit
    other = _agent_by_id(offer["from_agent"])
    seller, buyer = (me, other) if me["role"] == "seller" else (other, me)
    room = seller["trade_cap_kwh"] - _committed_kwh(seller["agent_id"], offer["step_from"], offer["step_to"])
    if offer["kwh_per_step"] > room + 1e-9:
        conn_().execute("UPDATE offers SET status = 'rejected' WHERE offer_id = ?", (offer_id,))
        conn_().commit()
        return {"ok": False, "reason": f"{seller['agent_id']} no longer has the cap; offer rejected"}
    n_steps = offer["step_to"] - offer["step_from"] + 1
    stake = offer["penalty_usd_mwh"] * offer["kwh_per_step"] * n_steps / 1000  # $/MWh x kWh -> $
    conn_().execute("UPDATE offers SET status = 'accepted' WHERE offer_id = ?", (offer_id,))
    cur = conn_().execute(
        "INSERT INTO commitments (offer_id, seller, buyer, step_from, step_to, kwh_per_step, "
        "price_usd_mwh, penalty_usd_mwh, stake_usd) VALUES (?,?,?,?,?,?,?,?,?)",
        (offer_id, seller["agent_id"], buyer["agent_id"], offer["step_from"], offer["step_to"],
         offer["kwh_per_step"], offer["price_usd_mwh"], offer["penalty_usd_mwh"], stake))
    cid = cur.lastrowid
    conn_().execute("UPDATE agents SET stake_locked_usd = stake_locked_usd + ? WHERE agent_id = ?",
                 (stake, seller["agent_id"]))
    payload = {"commitment_id": cid, "offer_id": offer_id, "seller": seller["agent_id"],
               "buyer": buyer["agent_id"], "step_from": offer["step_from"], "step_to": offer["step_to"],
               "kwh_per_step": offer["kwh_per_step"], "price_usd_mwh": offer["price_usd_mwh"],
               "penalty_usd_mwh": offer["penalty_usd_mwh"], "stake_usd": round(stake, 2)}
    seq = _log(me["agent_id"], "commit", payload)
    return {"ok": True, "commitment_id": cid, "stake_usd": round(stake, 2), "ledger_seq": seq}


@mcp.tool()
def get_inbox(token: str) -> dict:
    """Open offers waiting for your answer, and the status of offers you sent."""
    me = _agent(token)
    if not me:
        return {"ok": False, "reason": "unknown token"}
    incoming = conn_().execute("SELECT * FROM offers WHERE to_agent = ? AND status = 'open'",
                            (me["agent_id"],)).fetchall()
    sent = conn_().execute("SELECT * FROM offers WHERE from_agent = ? ORDER BY offer_id DESC LIMIT 10",
                        (me["agent_id"],)).fetchall()
    return {"ok": True, "round": _round(), "incoming": [dict(r) for r in incoming],
            "sent": [dict(r) for r in sent]}


@mcp.tool()
def get_ledger(token: str, since_seq: int = 0, limit: int = 100) -> dict:
    """Public ledger: every registration, offer, commitment, settlement and challenge,
    oldest first. Pass since_seq to page."""
    if not _agent(token):
        return {"ok": False, "reason": "unknown token"}
    rows = ledger.entries(conn_(), since_seq)[:limit]
    return {"ok": True, "entries": [{k: r[k] for k in ("seq", "ts", "agent_id", "action", "payload")} for r in rows]}


@mcp.tool()
def challenge(token: str, commitment_id: int, claim: str, evidence: str) -> dict:
    """Auditors only. Contest a commitment, e.g. claim="envelope exceeds nameplate",
    evidence="declared 4870 kW vs 2435 kW battery". The server adjudicates
    deterministically: a valid challenge pays you a bounty from the seller's stake and
    cuts its reputation; an invalid one costs you a bond."""
    me = _agent(token)
    if not me:
        return {"ok": False, "reason": "unknown token"}
    if me["role"] != "auditor":
        return {"ok": False, "reason": "only auditors may challenge"}
    c = conn_().execute("SELECT * FROM commitments WHERE commitment_id = ?", (commitment_id,)).fetchone()
    if not c:
        return {"ok": False, "reason": "no such commitment"}
    from gridpact import settle
    with _write:  # adjudication reads and updates stake/reputation: serialise it like the other writes
        verdict = settle.adjudicate(conn_(), c, me["agent_id"], claim, evidence)
        conn_().commit()
    return {"ok": True, **verdict}


# --- admin (called by the orchestrator in-process, not over MCP) -------------

def set_round(n):
    """Advance the negotiation round; offers older than OFFER_TTL_ROUNDS expire."""
    c = db.connect()
    c.execute("INSERT OR REPLACE INTO kv VALUES ('round', ?)", (str(n),))
    expired = c.execute("UPDATE offers SET status = 'expired' WHERE status = 'open' AND round_opened <= ? "
                        "RETURNING offer_id", (n - OFFER_TTL_ROUNDS,)).fetchall()
    for r in expired:
        ledger.append(c, "gridpact", "expire", {"offer_id": r["offer_id"], "round": n})
    c.commit()
    c.close()


def launch(timeout=15):
    """Start the server as a subprocess and wait until the port answers. Returns the Popen."""
    import os
    log_path = os.environ.get("GRIDPACT_SERVER_LOG", ROOT / "server.log")   # per-run file in the benchmark
    proc = subprocess.Popen([sys.executable, "-m", "gridpact.server"], cwd=ROOT,  # importable from any cwd
                            stdout=subprocess.DEVNULL, stderr=open(log_path, "w"))  # errors land in server.log
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", PORT), timeout=0.5).close()
            return proc
        except OSError:
            time.sleep(0.2)
    proc.kill()
    raise RuntimeError("GridPact server did not start")


if __name__ == "__main__":
    mcp.run("streamable-http", port=PORT)
