# GridPact (HW6 MVP)

Peer-to-peer energy trading protocol for ENGIE grid agents: 4 Haiku agents call an MCP server;
deterministic settlement and an independent verifier. Spec in `PLAN.md`, status in `docs/PROGRESS.md`.

## Setup
- `python3.13 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- `.env`: `ANTHROPIC_API_KEY=...` and `GRIDPACT_DATA_DIR=<folder with the ENGIE parquet files>` (default `data/`)

## Run
- `python orchestrate.py --demo` — reset DB, run one day with the LLM agents (~$0.01), then verify
- `python verify.py` — re-check the last run independently (exit 1 on any FAIL)
- `docs/AGENT_GUIDE.md` is the guide for outside agents (connect, tools, limits, example); keep it in step with `gridpact/server.py`
- `python -m coldstart.run_env --out coldstart/runs/<name>` then `python -m coldstart.check ...` — HW9 cold-start test (plan in `coldstart/PLAN.md`)
- `python demo_deposits.py [--no-audit]` — 2-minute walkthrough of deposits, the auditor and settlement (no LLM, no data, no key)
- `python -m gridpact.server` — just the MCP server at http://127.0.0.1:8765/mcp

## Test
- `pytest` — ledger, settlement, adjudication and trim tests
- `python -m tests.smoke_client` — one trade over MCP without an LLM
- No ENGIE data? `GRIDPACT_DATA_DIR=fixtures/synthetic` runs the server, smoke client and `tests/test_fixture_day.py` on made-up numbers (`python -m gridpact.fixture` regenerates them)

## Benchmark (HW7, `benchmark/`)
- Spec: `benchmark/PREREGISTRATION.md` (fixed before runs; amendments dated). Results: `benchmark/README.md`.
- `python -m benchmark.run --condition both --scenario <id|tuning|heldout|stress|all> --seeds 5 --parallel 4 --version vN` (~$0.005/run, resumable, stops at the $15 cap)
- `python -m benchmark.score --version vN && python -m benchmark.analyze --version vN && python -m benchmark.stress --version vN && python -m benchmark.compare`
- Keep `benchmark/runs/` in git (logs); `*.db`, `server.log`, `stdout.log` inside it stay ignored.

## Rules
- Truth columns (`anomaly_flag`, `*_true_*`) are read only in `verify.py`.
- Never commit `.env`, `*.db`, `runs/`, `server.log`, or the ENGIE data.
- Log non-obvious choices in `docs/DECISIONS.md`; tick phases in `docs/PROGRESS.md`.
