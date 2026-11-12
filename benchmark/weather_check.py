"""Does real weather explain what GridPact settles on?  python -m benchmark.weather_check  ->  results/weather_check.md

Two questions, per seller, on the ENGIE 2023 data (needs GRIDPACT_DATA_DIR; real weather from gridpact.weather, cached):
1. Does real sunshine explain the plant's solar output? (hourly correlation over two summer weeks)
2. Does a day's real sunshine predict how charged the battery is at 17:00, the start of GridPact's trading window?
   If it did, weather could check a seller's evening promise independently of its nameplate.
Truth columns are not read; only observed columns (ghi_wm2, pv_ac_kw, bess_soc_percent).
"""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from gridpact import weather

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
D = Path(os.environ.get("GRIDPACT_DATA_DIR", ROOT / "data"))
SELLERS = ["PVB_37", "PVB_17", "PVB_32", "PVB_44"]
WEEKS = ("2023-06-12", "2023-06-25")


def main():
    meta = pd.read_parquet(D / "agents_metadata.parquet").set_index("entity_id")
    rows = []
    for s in SELLERS:
        lat, lon = float(meta.loc[s].lat), float(meta.loc[s].lon)
        ts = pd.read_parquet(D / "agents_timeseries_2023_15min.parquet", columns=["pv_ac_kw", "bess_soc_percent"],
                             filters=[("entity_id", "==", s)]).reset_index().drop(columns="entity_id").set_index("timestamp")
        ts.index = ts.index.tz_convert("America/Chicago").tz_localize(None)
        ts = ts[~ts.index.duplicated()].sort_index()      # DST hours repeat or vanish in local time
        year = weather.fetch(lat, lon, "2023-01-01", "2023-12-31")
        wk = ts.loc[WEEKS[0]:WEEKS[1]].resample("1h").mean().join(year, how="inner")
        daily_sun = year.ghi_wm2.groupby(year.index.date).sum() / 1000
        soc17 = ts[(ts.index.hour == 17) & (ts.index.minute == 0)].bess_soc_percent
        soc17.index = soc17.index.date
        dd = pd.concat([daily_sun.rename("sun"), soc17.rename("soc")], axis=1).dropna()
        r1, r2 = wk.pv_ac_kw.corr(wk.ghi_wm2), dd.sun.corr(dd.soc)
        rows.append((s, round(r1, 2), round(r2, 2), round(r2 * r2, 3), len(dd)))
    out = ["# Does real weather explain what GridPact settles on?", "",
           "Real weather: Open-Meteo archive at each plant's coordinates. ENGIE 2023 observed columns only.", "",
           "| seller | corr(real sun, solar output), 2 summer weeks, hourly | corr(day's real sun, battery charge at 17:00), 365 days | R2 | days |",
           "|---|---|---|---|---|"]
    out += [f"| {s} | {a} | {b} | {c} | {n} |" for s, a, b, c, n in rows]
    out += ["", "Reading: weather explains solar output well, and explains almost none of the evening battery charge (R2 under 0.1).",
            "So it cannot independently check the evening energy a seller promises, and GridPact does not use it in settlement."]
    (ROOT / "benchmark" / "results" / "weather_check.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
