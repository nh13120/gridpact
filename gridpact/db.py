"""SQLite state for GridPact. One file, plain SQL, no ORM.

Pattern note: `sqlite3` is in Python's standard library. `connect()` opens the
database and creates any missing tables, so every other module just calls it.
Rows come back as `sqlite3.Row`, which lets you write row["kwh"] like a dict.
"""
import sqlite3

from gridpact.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    agent_id          TEXT PRIMARY KEY,
    role              TEXT NOT NULL,          -- buyer | seller | auditor
    token             TEXT NOT NULL UNIQUE,   -- secret returned once by register_agent
    bus               INTEGER,
    bess_power_kw     REAL,                   -- nameplate, from the public registry (metadata)
    bess_energy_kwh   REAL,
    declared_flex_kw  REAL,                   -- what the agent CLAIMS it can deliver (may be a lie)
    flex_duration_h   REAL,
    reputation        REAL NOT NULL DEFAULT 1.0,
    trade_cap_kwh     REAL,                   -- max kWh per step this agent may commit
    balance_usd       REAL NOT NULL DEFAULT 0, -- running P&L from trades, penalties, bounties
    stake_locked_usd  REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS offers (
    offer_id        INTEGER PRIMARY KEY,
    from_agent      TEXT NOT NULL,
    to_agent        TEXT NOT NULL,
    step_from       INTEGER NOT NULL,
    step_to         INTEGER NOT NULL,         -- inclusive
    kwh_per_step    REAL NOT NULL,
    price_usd_mwh   REAL NOT NULL,
    penalty_usd_mwh REAL NOT NULL,            -- paid per MWh of shortfall
    status          TEXT NOT NULL DEFAULT 'open', -- open | accepted | rejected | expired
    round_opened    INTEGER NOT NULL DEFAULT 0,
    request_id      TEXT                      -- optional client key: a retried propose returns the same offer
);
CREATE TABLE IF NOT EXISTS commitments (
    commitment_id   INTEGER PRIMARY KEY,
    offer_id        INTEGER NOT NULL UNIQUE,   -- one commitment per offer, enforced by SQLite
    seller          TEXT NOT NULL,
    buyer           TEXT NOT NULL,
    step_from       INTEGER NOT NULL,
    step_to         INTEGER NOT NULL,
    kwh_per_step    REAL NOT NULL,
    price_usd_mwh   REAL NOT NULL,
    penalty_usd_mwh REAL NOT NULL,
    stake_usd       REAL NOT NULL,            -- penalty x total kWh, locked from the seller
    status          TEXT NOT NULL DEFAULT 'active', -- active | challenged
    trimmed_from_kwh REAL                     -- v2: kWh/step before a valid challenge cut it to the real cap
);
CREATE TABLE IF NOT EXISTS settlements (
    id              INTEGER PRIMARY KEY,
    commitment_id   INTEGER NOT NULL,
    step            INTEGER NOT NULL,
    committed_kwh   REAL NOT NULL,
    delivered_kwh   REAL NOT NULL,
    shortfall_kwh   REAL NOT NULL,
    energy_usd      REAL NOT NULL,            -- buyer -> seller for delivered energy
    penalty_usd     REAL NOT NULL,            -- seller stake -> buyer for the shortfall
    grid_usd        REAL NOT NULL             -- buyer -> grid for the missing energy
);
CREATE TABLE IF NOT EXISTS challenges (
    id              INTEGER PRIMARY KEY,
    commitment_id   INTEGER NOT NULL,
    auditor         TEXT NOT NULL,
    claim           TEXT NOT NULL,
    evidence        TEXT NOT NULL,
    verdict         TEXT,                     -- valid | invalid
    bounty_usd      REAL NOT NULL DEFAULT 0
);
-- at most one valid challenge per commitment, enforced by SQLite even under concurrent calls
CREATE UNIQUE INDEX IF NOT EXISTS one_valid_challenge ON challenges(commitment_id) WHERE verdict = 'valid';
CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT);
-- messages about changes to an agent's commitments; the server attaches the undelivered ones to the agent's next reply
CREATE TABLE IF NOT EXISTS notices (
    id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL, text TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS ledger (
    seq          INTEGER PRIMARY KEY,
    ts           TEXT NOT NULL,
    agent_id     TEXT NOT NULL,
    action       TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    prev_hash    TEXT NOT NULL,
    hash         TEXT NOT NULL
);
"""


def connect(path=DB_PATH):
    """Open (and create if needed) the database. Callers must conn.commit() after writes."""
    # check_same_thread=False: the MCP server calls tools from worker threads
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    if "request_id" not in {r[1] for r in conn.execute("PRAGMA table_info(offers)")}:   # database from before HW8
        conn.execute("ALTER TABLE offers ADD COLUMN request_id TEXT")
    # one offer per (sender, request_id); offers without a request_id are not constrained
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_offer_per_request ON offers(from_agent, request_id) "
                 "WHERE request_id IS NOT NULL")
    return conn


def reset(path=DB_PATH):
    """Delete the database file so a run starts clean."""
    import os
    if os.path.exists(path):
        os.remove(path)
