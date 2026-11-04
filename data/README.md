# Data

The ENGIE dataset is **not committed** (170 MB, sponsor data). Get it from Nicolas (shared drive link in the team chat) and put these files here:

- `agents_metadata.parquet`
- `agents_timeseries_2023_15min.parquet`
- `system_prices_and_load_2023_15min.parquet`

If you cannot get the data (it is sponsor data and not redistributable), the committed run logs under `benchmark/runs/v1` and `v2` plus `benchmark/results/` let you check every reported number without re-running; re-running needs the three files and an `ANTHROPIC_API_KEY`.

Or keep them anywhere and set `GRIDPACT_DATA_DIR=/path/to/folder` in `.env`.
Column meanings: see `docs/DATA_NOTES.md`.
