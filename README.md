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

## Limitations and next steps

Filled in at Phase 6.
