# Decisions

One or two lines each. Newest at the bottom.

- **Repo layout and scope** follow `PLAN.md` (HW6 slice: 4 agents, 1 day, no coalitions / faults / pandapower).
- **Data location**: `GRIDPACT_DATA_DIR` in `.env`, default `data/`. Nicolas points it at his existing copy; Maheen copies the files into `data/`.
- **Agents COM_09 / PVB_17 / PVB_37, day 2023-06-19**: the liar's shortfall only shows if the buyer needs more than the liar's real battery; COM_04 (the proposal's example) is too small. See `docs/DATA_NOTES.md`.
- **"Same area" = nearest by lat/lon**: the grid has one zone and no agent sits behind a distribution transformer.
- **Delivery = metadata battery limits, not re-simulated dispatch**: `min(committed, bess_power_kw x 0.25)` per step. Honest about it in the README as the limitation.
- **Price spread**: one grid fee (30 $/MWh) on imports. The proposal sweeps spreads; one value is enough for HW6.
- **Liar = honest data + inflated declared envelope** stored at `register_agent`. Swap for ENGIE's malicious dataset later behind the same field.
- **Stake, reputation, balance are columns on `agents`**, not separate tables: one row per agent is easier to read and update. A `challenges` table was added since Phase 4 needs it.
- **Ledger hash covers the whole entry** (seq, ts, agent, action, payload), not just the payload, so editing any field is caught.
- **Stake is locked at acceptance**, not at proposal: one place to compute it (`penalty x kWh x steps`), and a rejected offer never ties up money.
- **Tool results are JSON text**: `mcp` 2.x returns a `dict` as `content[0].text`; clients `json.loads` it. Agents read it as text anyway.
- **`find_counterparties` has no area filter** for HW6: the three physical agents were chosen as neighbours. Marked `ponytail:` in the code.
- **Server DB connection is opened lazily** and with `check_same_thread=False`: MCP runs tools in worker threads, and the orchestrator resets the DB file before the server starts.
- **Known limitation, identity**: anyone who registers an ID first owns it (token, not signature). Fine for a demo the orchestrator drives; the December version needs pre-shared keys or signatures. Role must match the agent type (a PVB can't register as buyer).
- **Inputs must be finite** (`math.isfinite`): NaN compares False to everything and would slip past the cap check. Writes are serialised with one lock so two accepts can't both pass the cap.
- **Owners register agents, not the LLMs.** First run: Haiku playing the liar refused to register an inflated envelope. Now the orchestrator (the "owner") registers each agent with its declared envelope (liar = 2x real), which also mirrors ENGIE's malicious dataset corrupting what an agent reports. The liar LLM is framed as the scripted adversarial seller in a fraud-detection test and sells into the inflated cap; Haiku accepts that framing.
- **Register before the buyer's first turn**: the first run wasted a round because the buyer went first and found no sellers.
- **Trade caps are whole kWh** (`floor`): the LLM proposed 1364 against a cap of 1363.66 and got refused.
- **Agent SDK settings**: `tools=[]` (no built-in tools), `allowed_tools=["mcp__gridpact__*"]`, `setting_sources=[]` (ignore ~/.claude), `max_turns=8`, `max_budget_usd=2`. A full day costs about a cent on Haiku 5.5.
- **The "liar" LLM is not asked to lie.** Haiku refused in 2 of 3 runs to overcommit when it knew the real battery size, even framed as a fraud-detection test ("I declined to play the overcommitting seller"). So the lie lives entirely in the owner's registration (declared envelope = 2x nameplate) and the LLM is a greedy seller that trusts its registered cap. This matches ENGIE's threat model (corrupted reports) and is deterministic. Finding worth reporting: model honesty constrains how liars can be simulated.
- **Settlement delivery bound = registry nameplate** (`bess_power_kw x 0.25` per step, `bess_energy_kwh` over the window). Real-time price + grid fee prices the shortfall the buyer must cover.
- **Adjudication rule**: declared_flex_kw > 1.1 x nameplate -> valid. Bounty 10% of the commitment's stake from the seller's locked stake, reputation -0.5, cap reset to the real one; invalid challenge costs the auditor a $50 bond. One valid challenge per commitment.
- **`verify.py` restates constants and re-implements the hash** instead of importing them: if it imported `gridpact/`, a bug there would be verified against itself. The chosen day is read from the `kv` table, which `orchestrate.py` writes.
- **Truth columns are read only in `verify.py`**: `bess_power_true_kw` (max over the year) confirms each seller's real battery power; metadata `flex_up_kw` is the honest envelope.
- **Code review (Phase 6) fixes**: verify.py now derives "real" power from the truth column (not metadata), checks every expected step (a skipped step is a FAIL), flags commitments with no offer row, and shares power/energy budgets per seller across commitments (settle.py too). verify.py opens the DB read-only and fails fast if it is missing.

## Benchmark (HW7, `benchmark/`)

- **Preregistered before any run** (`benchmark/PREREGISTRATION.md`): claim, baseline, metrics, pass/fail, cases, seeds, budget. Changes after that are dated amendments in the same file.
- **Baseline = ablation, not a weaker agent**: same prompts, model, limits; `settle_day(trust=True)` pays on the claim, no penalty, no auditor. "Plain bilateral" baseline skipped: the only protocol rule that bites in negotiation is the cap check, and the liar's cap is already inflated.
- **Audit runs before settlement in the benchmark** (not after, as in `orchestrate.py`) so "caught before settlement" is literal; the scorer checks the ledger order.
- **Ground truth = metadata nameplate**, asserted equal to max `bess_power_true_kw` at scorer load; the scorer recomputes delivery itself, never trusts the DB's `delivered_kwh` (it checks it in gridpact runs).
- **Each run is a child process with its own port and DB** (`GRIDPACT_PORT`, `GRIDPACT_DB`): `gridpact.config` reads env once at import, so parallel runs need separate processes.
- **`register_agent` accepts any registry entity** (was hard-coded to the three HW6 ids).
- **The SDK's turn cap counts assistant messages, not tool calls**: a 2-turn auditor still filed two challenges by calling tools in parallel. And the SDK raises after delivering an `error_max_turns` result; `run_agent.py` keeps the turn.
- **Rounding trap found by the benchmark**: the ledger shows `declared_flex_kw` to one decimal (6837.4) and the auditor's task text gave the nameplate as a whole number (6837); twice the auditor challenged an honest seller over 0.4 kW and lost the bond. The auditor's prompt says "exceeds nameplate" while the server's rule is 1.1x, so a 1.08x liar was challenged 5/5 times and ruled invalid each time. Left as found in v1; documented, not fixed, because the Phase 3 evidence pointed elsewhere.
- **Haiku would not collude**: told it had a side deal with PVB_06, the auditor challenged PVB_06 anyway in 5/5 runs. Same model property that stopped it lying as a seller in HW6.
- **Where GridPact stops helping (v1 stress sweep)**: from 6 sellers the buyer fills its need on paper from the nearest four, two with doubled caps, and never contacts the honest rest; coverage stays at 65% in both conditions. Catching the liar refunds money but not energy. v2 change: a valid challenge trims the commitment to the real cap and the released volume goes back to market for one round.
- **v2 result**: delivery at 6-16 sellers rose from 65% to 81-90% of need, honest sellers trading doubled, and the held-out two-buyer case went from the honest seller idle (5/5) to trading (5/5). Two costs: re-sourced volume can reach a liar after the audit (recall 0.8 / 0.67 at 12 / 16 sellers; needs a second audit, not done), and the liar's loss shrank from ~$600 to the ~$100 bounty. Claim P1-P6 holds in both versions. Full write-up: `benchmark/README.md`.
- **Trim only touches unsettled commitments** (`settle.trim_to_real_cap`): a challenge after settlement changes nothing, so "caught before settlement" has a literal consequence.

## HW8: synthetic fixture instead of the sponsor data (2026-11-05)
The ENGIE parquet files are sponsor data (136 MB) and cannot go in a public PR. `gridpact/fixture.py` writes tiny made-up files with the same names and columns, so `GRIDPACT_DATA_DIR=fixtures/synthetic` is all a reviewer needs. data.py and verify.py are unchanged. Found while testing: a retried `propose` is not deduplicated (`tests/test_fixture_day.py`).
