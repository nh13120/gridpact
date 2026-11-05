# GridPact

A shared trading and verification layer for ENGIE's grid agents. Self-interested energy agents
(communities, data centers, solar + battery plants) find counterparties, negotiate day-ahead energy
trades, and are settled every 15 minutes against delivered energy. An agent that overstates what it
can deliver pays shortfalls from a locked stake, and an auditor agent that proves the false claim
earns a bounty while the liar loses reputation and trading cap. Every action is on a hash-chained ledger.

**This repo is the HW6 MVP** (MIT MAS.665): one simulated day from the ENGIE dataset, four LLM agents
(buyer, honest seller, lying seller, auditor) calling GridPact through MCP, deterministic settlement,
and an independent verifier. Status: all six phases done (`docs/PROGRESS.md`).

**HW7 benchmark**: `benchmark/` holds the preregistered evaluation (claim, ablation baseline, 15 scenarios,
stress sweep, one evidence-driven change, retest on held-out cases) with every run log. Start with
`benchmark/README.md`.

Git tags tell the two homeworks apart: `hw6` is the HW6 system as handed in (everything outside
`benchmark/`); `v1` is HW7 before its one change to the system; `v2` is after it. `git diff hw6 v1`
shows the small hooks HW7 added, `git diff v1 v2` the change itself.

## Setup (fresh clone)

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in ANTHROPIC_API_KEY
```

Data: put the three ENGIE parquet files in `data/` (see `data/README.md`), or set
`GRIDPACT_DATA_DIR=/path/to/folder` in `.env`. The data is not in the repo.

## Run

```bash
python orchestrate.py --demo  # the one command: reset DB, run the day, verify (~$0.01 of Haiku)
python verify.py              # re-check the last run independently (exit 1 on any FAIL)
pytest                        # ledger hash-chain unit tests
python -m tests.smoke_client  # one trade over MCP without an LLM (no API key needed)
python -m gridpact.data       # print the chosen day for the 3 physical agents
```

### What the demo output means

1. **Registration (by owners).** `COM_09` (buyer), `PVB_17` (honest seller), `PVB_37` (seller whose owner
   declared a flexibility envelope of ~4,869 kW against a real 2,435 kW battery), `AUD_01` (auditor).
2. **Negotiation round(s).** Each `=== agent ===` block is one Haiku turn; each `-> tool(...)` line is a
   real MCP call to the server. The buyer proposes at each seller's cap; sellers accept or counter.
3. **Settlement.** Plain code, no LLM: per 15-min step, `delivered = min(committed, battery nameplate)`.
   The liar committed 1,217 kWh/step but can deliver 609, so it pays ~$500 of penalties from its stake.
4. **Audit.** The auditor reads the ledger, sees `declared_flex_kw` 4,869 vs nameplate 2,435, and
   challenges. The server adjudicates: valid, bounty paid, reputation 1.0 -> 0.5, cap reset to 608.
5. **P&L.** Buyer pays ~$1,090 for ~31 MWh that would have cost ~$2,260 from the grid; the honest
   seller keeps its stake; the liar ends negative.
6. **verify.py** prints six `[PASS]`/`[FAIL]` lines (see below). Exit code 0 means everything checks out.

Every tool call and result is also written to `runs/<timestamp>/transcript.jsonl`.

## How it is built

```
agents/run_agent.py (Claude Agent SDK, Haiku 5.5, one process per turn)
   |  MCP tool calls (streamable HTTP, http://127.0.0.1:8765/mcp)
   v
gridpact/server.py (7 tools)  --->  gridpact.db (SQLite: agents, offers, commitments, settlements, challenges, ledger)
                                        ^
gridpact/settle.py (deterministic) -----+---- reads ENGIE parquet (obs columns)
verify.py (independent; imports nothing from gridpact/; the only reader of truth columns)
```

Rules are enforced by the server, not by prompts: an agent acts only as itself (token), can commit
only up to its declared cap net of existing commitments, stake = penalty x kWh is locked at acceptance,
one valid challenge per commitment.

## Repo map

| Path | What |
|---|---|
| `PLAN.md` | the spec: scope, architecture, phases |
| `CLAUDE.md` | setup / run / test commands for Claude Code sessions |
| `docs/DATA_NOTES.md` | columns used, chosen agents and day, how surplus and delivery are computed |
| `docs/DECISIONS.md` | short log of design choices and what we learned |
| `docs/PROGRESS.md` | phase checklist |
| `gridpact/config.py` | settings read from `.env` (data dir, port, grid fee) |
| `gridpact/data.py` | loads one day of ENGIE data (obs columns only) |
| `gridpact/db.py` | SQLite tables |
| `gridpact/ledger.py` | append-only hash-chained log; `verify_chain()` finds the first tampered entry |
| `gridpact/server.py` | the MCP server: 7 tools agents call, rules enforced server-side |
| `gridpact/settle.py` | deterministic 15-min settlement and challenge adjudication |
| `agents/prompts/*.md` | system prompts: buyer, honest_seller, liar, auditor |
| `agents/run_agent.py` | one agent turn via the Claude Agent SDK; logs to `runs/<ts>/transcript.jsonl` |
| `orchestrate.py` | the whole day: register -> negotiate -> settle -> audit -> P&L; `--demo` resets and verifies |
| `verify.py` | independent checks: hash chain, settlements from raw data, truth columns, economics |
| `tests/` | ledger unit tests and the no-LLM smoke client |

## The six verification checks

1. Ledger hash chain intact end to end (re-implemented, not imported).
2. Every settlement step recomputed from the raw parquet and matched to the cent, including missing steps.
3. Truth column `bess_power_true_kw` confirms who really overstated, and that exactly those sellers were challenged.
4. Buyer paid less than buying the same kWh from the grid.
5. The liar's P&L is below what it would have earned declaring honestly.
6. No settlement without an accepted commitment; no duplicate steps.

## Limitations (honest list)

- **The recorded ENGIE year does not react to trades.** Delivery is bounded by the battery's registry
  nameplate (power per step, energy over the day), not by re-simulating its dispatch. The December
  version needs the re-simulator and pandapower line checks.
- **The liar's lie is in the registration, not in the LLM.** Haiku refused to overcommit knowingly in
  2 of 3 runs, so the owner registers the inflated envelope and the LLM is a greedy seller trusting it.
  This matches ENGIE's threat model (corrupted reports) but means we did not demonstrate a scheming LLM.
- **Identity is a token, not a signature.** Whoever registers an ID first owns it.
- **Three physical agents, one day, one price spread, no area filter.** `find_counterparties` returns
  everyone; the demo agents were chosen to be neighbours.
- The auditor's rule (declared > 1.1 x nameplate) is the only fraud it can detect.

## Next steps toward the December demo

Re-simulator for battery dispatch under the agreed schedule; pandapower line-loading check before
commitment; `grant_mandate` and coalitions; `report_fault` with the tolerance band; telemetry-based
auditing (freeze / surge / SOC-recalibration lies); 12 agents, one week, several seeds and price
spreads; metrics from the proposal (energy kept local, fraudulent kWh settled, time to catch a liar).

## Team

Nicolas (protocol, ledger, MCP, agents; for HW7 the preregistration, benchmark harness, runs and the v2 change) and Maheen
(HW6 audit fixes: bounty accounting, money-conservation check, settlement tests; HW7 write-up and report).
MAS.665 AI Studio, fall 2026.
