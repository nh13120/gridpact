# GridPact — HW6 MVP Plan (MAS.665 AI Studio)

## Context for Claude Code

GridPact is a shared trading and verification layer for ENGIE's grid agents. Self-interested energy agents (communities, data centers, solar+battery plants) find counterparties, negotiate day-ahead energy trades, and get settled every 15 minutes against metered delivery. Agents that lie lose their stake and reputation when an auditor agent challenges them.

HW6 asks for a **working agentic core**: real agents calling GridPact through its real interface, real execution, a result the agents use, a meaningful correctness check, and one stated limitation. No UI needed. Terminal output and logs are enough.

Two people will work from this repo: Nicolas (building now) and his teammate Maheen (will clone it from GitHub, read it, and continue). Write everything so Maheen can understand and run it without asking Nicolas. Both are early Python users. Keep code simple and flat, comment intent, avoid clever abstractions, and explain any unfamiliar pattern in a short note when you introduce it. After each phase, tell the user the exact command to run and what output to expect.

## Scope decision

The full GridPact design has 12 agents, a coalition, mandates, pandapower line checks, a dispatch re-simulator and a one-week run. That is the December demo for ENGIE, not Wednesday's. For HW6, build one thin slice that runs end to end:

- 4 LLM agents: 1 buyer (community), 1 honest seller (solar+battery), 1 lying seller (overclaims its flexibility), 1 auditor
- 1 simulated day (96 × 15-min steps) from the ENGIE dataset
- Full cycle on the ledger: discover → negotiate → commit → settle → challenge → penalty

Out of scope for HW6: `grant_mandate` / coalitions, `report_fault`, pandapower, the re-simulator, FastAPI wrapper, real cryptographic signatures, multiple seeds, demo video.

## Architecture

```
agents (Claude Agent SDK, one process per turn)
   │  MCP tool calls (streamable HTTP)
   ▼
gridpact/server.py  (MCPServer)
   │  reads/writes
   ▼
gridpact.db (SQLite): agents, offers, commitments, stakes, reputation, ledger
   ▲
settle.py (deterministic, no LLM) ── reads ENGIE parquet ── writes settlement + penalties to ledger
verify.py (independent check, does NOT import server code)
```

Why this shape: MCP is the interface agents actually use, so the demo shows agents calling a product, not a script pretending to be one. Settlement is plain code because it must be deterministic and auditable. The verifier is separate so it can catch bugs in the server instead of repeating them.

## Repo layout

```
gridpact/
  README.md              # start here: what it is, setup, how to run, status
  PLAN.md                # this file
  docs/
    DATA_NOTES.md        # written in Phase 0
    DECISIONS.md         # short log of design choices and why
    PROGRESS.md          # phase checklist + what's next
  requirements.txt       # pinned versions
  .env.example           # ANTHROPIC_API_KEY=
  .gitignore             # data/, .env, *.db, runs/, .venv/, __pycache__/
  data/
    README.md            # where to get the ENGIE files and where to put them
  gridpact/
    config.py            # settings from .env
    db.py                # SQLite schema + helpers
    ledger.py            # append-only hash-chained log
    server.py            # MCP server and tools
    settle.py            # 15-min settlement + adjudication
    data.py              # load one day of ENGIE data for chosen agents
  agents/
    prompts/             # buyer.md, honest_seller.md, liar.md, auditor.md
    run_agent.py         # runs one agent turn against the MCP server
  tests/
  orchestrate.py         # runs the full day: negotiation rounds → settle → audit
  verify.py
```

## Phase 0 — Repo setup and data inspection

Repo setup:
1. `git init`, create the layout above, `.gitignore`, `.env.example`, a virtual env, and pinned `requirements.txt`.
2. Write a first `README.md` skeleton (sections filled in as phases land) and `docs/PROGRESS.md` with the phase checklist.
3. Write `data/README.md`: the ENGIE dataset is not committed (size and sponsor data). Say which files go in `data/` and where teammates get them.
4. Do **not** create a GitHub remote or push. That happens in Phase 6 with the user's approval.

Data inspection (don't guess):
1. Load the ENGIE parquet files. List files, columns, dtypes, row counts, and the agent ID / bus / asset-type metadata.
2. Confirm the column names for: net power at the connection (`p_net_kw`), PV output, battery state of charge, battery capacity, anomaly flag, and the observation vs. ground-truth column split.
3. Pick the 3 physical agents for the demo: one community near two solar+battery plants. Pick a day where the plants have clear evening surplus.
4. Write `docs/DATA_NOTES.md`: columns used, chosen agent IDs, chosen date, and how "available surplus" per 15-min step is computed.

Done when: `python -m gridpact.data` prints the chosen day's surplus/deficit for the 3 agents in a small table. **If a needed column doesn't exist, stop and ask the user before inventing a substitute.**

## Phase 1 — Core state and ledger

- `db.py`: SQLite tables `agents`, `offers`, `commitments`, `stakes`, `reputation`, `ledger`, `settlements`.
- `ledger.py`: every state-changing action appends `{seq, ts, agent_id, action, payload_json, prev_hash, hash}` where `hash = sha256(prev_hash + canonical_json)`. No updates or deletes.
- Agent identity: `register_agent` returns a random token; every later call must pass it. Call this "authenticated agent IDs" in docs, not signatures.

Done when: `pytest tests/test_ledger.py` passes, including a test that appends 5 entries, tampers with entry 3, and the chain check fails at entry 3.

## Phase 2 — MCP server

Tools (typed inputs, typed errors with a clear `reason` field):

| Tool | Does |
|---|---|
| `register_agent(agent_id, role)` | Binds an ENGIE agent ID to a token; loads bus, area, battery size, declared envelope |
| `find_counterparties(token, side, window)` | Returns agents in the same area with reputation and trade cap |
| `propose(token, to, window, kwh, price, penalty)` | Opens an offer; validates kWh ≤ declared envelope and cap; locks stake |
| `respond(token, offer_id, action, counter_price?)` | accept / counter / reject; accept creates a commitment ID |
| `get_inbox(token)` | Open offers and counters addressed to this agent |
| `get_ledger(token, since_seq?)` | Public ledger entries |
| `challenge(token, commitment_id, claim, evidence)` | Auditor contests a claim; adjudicated in Phase 4 |

Rules enforced server-side, not by prompt: agents can only commit for their own bus; offers expire after N rounds; stake = penalty × kWh locked at commitment.

Done when: a plain Python MCP client script (no LLM) completes register → find → propose → accept and the ledger shows 4+ entries.

## Phase 3 — Agents and orchestration

- Use the **Claude Agent SDK** (Python) with the GridPact server configured as an MCP server. Model: `claude-haiku-5-5` for cost; switch to Sonnet only if negotiation quality is bad. Check the current SDK docs before writing this, since APIs move.
- Prompts:
  - `buyer.md`: cover an evening deficit cheaper than the grid import price; never accept above it.
  - `honest_seller.md`: sell real surplus above the export price; declare its true envelope.
  - `liar.md`: maximize revenue; declare an envelope ~2× its real surplus and sell into it.
  - `auditor.md`: read the ledger and public telemetry (obs columns only), challenge commitments whose claims don't match telemetry, earn bounties.
- `orchestrate.py`: day-ahead negotiation in rounds (buyer → sellers → buyer, max 4 rounds), then run `settle.py` over 96 steps, then one auditor turn, then print a final P&L table per agent.
- Log every tool call and result to `runs/<timestamp>/transcript.jsonl` and print a readable version to the terminal (agent name, tool, key args, result).

Done when: one `python orchestrate.py` run produces at least one commitment with each seller, without manual intervention.

## Phase 4 — Settlement and adjudication

- `settle.py`, per 15-min step per commitment: `delivered = min(committed_kwh_for_step, deliverable_from_data)`. Shortfall × penalty is paid from the seller's stake to the buyer in the same step. The grid covers the missing energy at import price.
- Adjudicate `challenge` deterministically: valid if the declared envelope exceeds the maximum physically possible from metadata + observed telemetry. Valid → bounty to auditor from stake, reputation cut, cap reduced. Invalid → auditor loses a small challenge bond.
- Truth columns are never read by server, settlement, or agents. Only `verify.py` may read them.

Done when: the liar ends the day with a shortfall, a valid challenge, and lower reputation; the honest seller has none of these.

## Phase 5 — Independent verification

`verify.py` must not import anything from `gridpact/`. It reads `gridpact.db` and the raw parquet and checks:

1. Ledger hash chain is intact end to end.
2. Recomputes every settlement from raw data and matches the stored values to the cent.
3. Uses truth columns to confirm the liar's envelope really was false and the honest seller's wasn't.
4. Economic outcome: buyer pays less than grid-only; liar's final P&L is below what it would have earned trading honestly (compute the honest counterfactual).
5. No settlement occurred without a matching accepted commitment.

Print each as PASS/FAIL with the numbers. This is the "meaningful check" for the rubric.

Add `python orchestrate.py --demo`: resets the DB, runs the full day, then runs `verify.py`, with readable output. This is the one command a teammate runs to see the whole thing work.

## Phase 6 — Handoff to Maheen

1. Finish `README.md`:
   - What GridPact is (3–4 sentences) and what this MVP slice does
   - Setup from a fresh clone: venv, install, `.env`, where to put the data
   - How to run: `python orchestrate.py --demo`, and what the output means
   - Repo map: one line per file
   - Current limitations (state the true one after the run; likely: the recorded ENGIE year doesn't react to trades, so delivery is approximated from battery nameplate limits instead of re-simulating battery dispatch)
   - Next steps toward the December demo (re-simulator, pandapower line checks, mandates/coalitions, `report_fault`, more agents and seeds)
2. Make sure `docs/DECISIONS.md` and `docs/PROGRESS.md` are current.
3. Do a fresh-clone test: clone the repo into a temp folder, follow the README exactly, and confirm the demo runs. Fix anything the README missed.
4. Ask the user before creating the GitHub repo. When approved: `gh repo create gridpact --private --source . --push`. The user adds Maheen as a collaborator.

## Working rules

- Build phases in order. Run the "done when" check before moving on and show the output.
- Commit after each phase with a message that says what changed and why. Maheen will read the history to follow the work.
- After each phase, update `docs/PROGRESS.md`, and add any non-obvious choice to `docs/DECISIONS.md` in 1–2 lines.
- Never commit `.env`, API keys, the ENGIE data, `*.db`, or `runs/`.
- Keep the whole thing under ~800 lines of Python. If something grows past that, flag it.
- Don't hard-code results anywhere. The rubric penalizes it, and `verify.py` should catch it.
- If the Agent SDK or MCP setup fights you for more than ~30 minutes, fall back to the Anthropic Messages API with tool use calling the same server through an MCP client, and tell the user.
