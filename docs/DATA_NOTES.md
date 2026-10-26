# Data notes (Phase 0)

Source: ENGIE hybrid energy dataset, 80 agents on a 200-bus grid, year 2023 at 15-minute steps.
Full column dictionary: the dataset's own `README.md` / `dataset_manifest.json`.

## Files and columns we use

| File | Columns | Used for |
|---|---|---|
| `agents_metadata.parquet` | `entity_id, entity_type, bus, lat, lon, bess_power_kw, bess_energy_kwh, flex_up_kw, flex_down_kw, flex_duration_h` | registry: bus, battery nameplate, honest flexibility envelope |
| `agents_timeseries_2023_15min.parquet` | `p_net_kw` (obs) | buyer deficit and seller surplus per step |
| `system_prices_and_load_2023_15min.parquet` | `price_da_usd_mwh`, `price_usd_mwh` | day-ahead price for negotiation, real-time price for settlement |

Columns are tagged **obs** (a real meter would show it) or **truth** (ground truth, grading only).
The server, settlement and agents read obs columns only. `verify.py` is the only file allowed to read
truth columns (`anomaly_flag`, `anomaly_observable`, `*_true_*`).

## Chosen agents

| ID | Role | Bus | Battery (kW / kWh) | Honest envelope `flex_up_kw` |
|---|---|---|---|---|
| `COM_09` | buyer (community, 28.6 MW peak) | 147 | 4,010 / 13,810 | 8,727 |
| `PVB_17` | honest seller (solar + battery) | 6 | 5,455 / 17,596 | 5,455 |
| `PVB_37` | lying seller (declares ~2x its envelope) | 140 | 2,435 / 8,378 | 2,435 |

"Same area": the buses table has a single `zone` and every agent sits on a 115/230 kV bus, so there is
no transformer area to read off. We take the two solar plants **nearest the community by lat/lon**
(`PVB_17` and `PVB_37` are the two nearest to `COM_09`). A graph-distance or pandapower check is December work.

Why this trio: the liar is only caught by settlement if the buyer needs more than the liar's real battery
can deliver. `COM_09` needs ~5,900 kWh per step in the evening; `PVB_37` can really deliver
2,435 kW x 0.25 h = 609 kWh per step but will claim ~1,217.

## Chosen day: 2023-06-19 (local time, America/Chicago)

Trading window: 17:00-19:45 local = steps 68..79 (step 0 = 00:00 local).
Evening totals: `COM_09` imports 71,298 kWh; `PVB_17` exports 21,771 kWh; `PVB_37` exports 2,533 kWh.
Day-ahead price 34-44 $/MWh, real-time 30-59 $/MWh in the window.
No injected battery fault hits any of the three agents that day (checked once with `anomaly_flag`
to pick a clean day; the flag is not used anywhere else).

## Derived quantities (`gridpact/data.py`)

- `surplus_kwh = max(p_net_kw, 0) x 0.25`, `deficit_kwh = max(-p_net_kw, 0) x 0.25` per step.
- Deliverable energy for a seller (Phase 4): at most `bess_power_kw x 0.25` kWh per step and
  `flex_up_kw x flex_duration_h` kWh over the window, both from metadata. The recorded battery
  dispatch is **not** re-simulated; that is the stated limitation of this MVP.
- Prices: sellers earn the wholesale price, the buyer pays wholesale + `GRID_FEE_USD_MWH` (30 $/MWh,
  in `gridpact/config.py`). That spread is what makes a local trade worth doing.
