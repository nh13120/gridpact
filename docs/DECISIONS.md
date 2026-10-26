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
