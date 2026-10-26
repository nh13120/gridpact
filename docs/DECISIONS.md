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
