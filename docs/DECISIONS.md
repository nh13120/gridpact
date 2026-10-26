# Decisions

One or two lines each. Newest at the bottom.

- **Repo layout and scope** follow `PLAN.md` (HW6 slice: 4 agents, 1 day, no coalitions / faults / pandapower).
- **Data location**: `GRIDPACT_DATA_DIR` in `.env`, default `data/`. Nicolas points it at his existing copy; Maheen copies the files into `data/`.
- **Agents COM_09 / PVB_17 / PVB_37, day 2023-06-19**: the liar's shortfall only shows if the buyer needs more than the liar's real battery; COM_04 (the proposal's example) is too small. See `docs/DATA_NOTES.md`.
- **"Same area" = nearest by lat/lon**: the grid has one zone and no agent sits behind a distribution transformer.
- **Delivery = metadata battery limits, not re-simulated dispatch**: `min(committed, bess_power_kw x 0.25)` per step. Honest about it in the README as the limitation.
- **Price spread**: one grid fee (30 $/MWh) on imports. The proposal sweeps spreads; one value is enough for HW6.
- **Liar = honest data + inflated declared envelope** stored at `register_agent`. Swap for ENGIE's malicious dataset later behind the same field.
