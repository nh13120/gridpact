# GridPact

A shared trading and verification layer for ENGIE's grid agents. Self-interested energy agents
(communities, data centers, solar + battery plants) find counterparties, negotiate day-ahead energy
trades, and are settled every 15 minutes against delivered energy. An agent that lies about what it can
deliver loses its stake and reputation when an auditor agent challenges it.

This repo is the **HW6 MVP** (MAS.665): one simulated day, four LLM agents (buyer, honest seller,
lying seller, auditor) calling GridPact through MCP, deterministic settlement on ENGIE data, and an
independent verifier. Status: see `docs/PROGRESS.md`.

## Setup (fresh clone)

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in ANTHROPIC_API_KEY
```

Data: put the ENGIE parquet files in `data/` (see `data/README.md`), or set `GRIDPACT_DATA_DIR` in `.env`.

## Run

```bash
python -m gridpact.data     # Phase 0: prints the chosen day for the 3 physical agents
pytest                      # Phase 1+: unit tests (ledger hash chain)
python -m gridpact.server   # Phase 2: run the MCP server (http://127.0.0.1:8765/mcp)
python -m tests.smoke_client  # Phase 2: start server + walk one trade without an LLM
python orchestrate.py --demo  # Phase 3+: reset DB, run the day with 4 Haiku agents (~$0.01)
```

(More commands are added as phases land. The final one-shot demo is `python orchestrate.py --demo`.)

## Repo map

| Path | What |
|---|---|
| `PLAN.md` | the spec: scope, architecture, phases |
| `docs/DATA_NOTES.md` | columns used, chosen agents and day, how surplus is computed |
| `docs/DECISIONS.md` | short log of design choices |
| `docs/PROGRESS.md` | phase checklist and what's next |
| `gridpact/config.py` | settings read from `.env` |
| `gridpact/data.py` | loads one day of ENGIE data (obs columns only) |
| `gridpact/db.py` | SQLite tables (agents, offers, commitments, settlements, challenges, ledger) |
| `gridpact/ledger.py` | append-only hash-chained log; `verify_chain()` finds the first tampered entry |
| `gridpact/server.py` | the MCP server: 7 tools agents call, rules enforced server-side |
| `tests/smoke_client.py` | no-LLM check: register -> find -> propose -> accept over MCP |
| `agents/prompts/*.md` | system prompts: buyer, honest_seller, liar (adversarial test agent), auditor |
| `agents/run_agent.py` | one agent turn via the Claude Agent SDK; logs tool calls to `runs/<ts>/transcript.jsonl` |
| `orchestrate.py` | the whole day: owners register -> negotiation rounds -> settlement -> audit -> P&L |

## Limitations and next steps

Filled in at Phase 6.
