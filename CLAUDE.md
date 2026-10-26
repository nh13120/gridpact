# GridPact (HW6 MVP)

Peer-to-peer energy trading protocol for ENGIE grid agents: 4 Haiku agents call an MCP server;
deterministic settlement and an independent verifier. Spec in `PLAN.md`, status in `docs/PROGRESS.md`.

## Setup
- `python3.13 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- `.env`: `ANTHROPIC_API_KEY=...` and `GRIDPACT_DATA_DIR=<folder with the ENGIE parquet files>` (default `data/`)

## Run
- `python orchestrate.py --demo` — reset DB, run one day with the LLM agents (~$0.01), then verify
- `python verify.py` — re-check the last run independently (exit 1 on any FAIL)
- `python -m gridpact.server` — just the MCP server at http://127.0.0.1:8765/mcp

## Test
- `pytest` — ledger hash-chain tests
- `python -m tests.smoke_client` — one trade over MCP without an LLM

## Rules
- Truth columns (`anomaly_flag`, `*_true_*`) are read only in `verify.py`.
- Never commit `.env`, `*.db`, `runs/`, `server.log`, or the ENGIE data.
- Log non-obvious choices in `docs/DECISIONS.md`; tick phases in `docs/PROGRESS.md`.
