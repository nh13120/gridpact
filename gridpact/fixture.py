"""Synthetic stand-in for the ENGIE parquet files, so the server and tests run without the sponsor data.

    python -m gridpact.fixture            # writes fixtures/synthetic/*.parquet (already committed)
    GRIDPACT_DATA_DIR=fixtures/synthetic python -m gridpact.server

Same file names and the columns GridPact and verify.py read. Every number is made up and round:
one buyer (COM_09), four sellers with different battery sizes, flat day-ahead and real-time prices
with an evening bump. The ids match the ENGIE ones so scenarios and docs read the same.
It is for integration tests (plumbing, idempotency, settlement arithmetic), not for results.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from gridpact.config import ROOT, TZ

OUT = ROOT / "fixtures" / "synthetic"
DAY = "2023-06-19"   # local day the server and verify.py settle by default
# entity_id, type, bus, battery kW, battery kWh, evening net kW (+ exports, - imports)
AGENTS = [
    ("COM_09", "community", 1, 0.0,    0.0,     -6000.0),
    ("PVB_17", "pv_bess",   2, 5000.0, 15000.0, 4000.0),
    ("PVB_37", "pv_bess",   3, 2500.0, 7500.0,  2000.0),
    ("PVB_32", "pv_bess",   4, 3000.0, 9000.0,  2400.0),
    ("PVB_50", "pv_bess",   5, 6000.0, 18000.0, 4800.0),
]


def build(out=OUT):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    meta = pd.DataFrame([{
        "entity_id": e, "entity_type": t, "bus": b, "lat": 40.0 + b * 0.01, "lon": -90.0 + b * 0.01,
        "bess_power_kw": kw, "bess_energy_kwh": kwh,
        "flex_up_kw": kw if kw else 8000.0, "flex_down_kw": kw if kw else 4000.0,
        "flex_duration_h": (kwh / kw) if kw else 6.0,
    } for e, t, b, kw, kwh, _ in AGENTS])
    meta.to_parquet(out / "agents_metadata.parquet", index=False)

    start = pd.Timestamp(DAY, tz=TZ).tz_convert("UTC") - pd.Timedelta(days=1)
    idx = pd.date_range(start, periods=96 * 3, freq="15min")        # the day before, the day, the day after
    local_hour = idx.tz_convert(TZ).hour
    evening = (local_hour >= 17) & (local_hour < 20)
    rows = []
    for e, t, b, kw, kwh, net in AGENTS:
        p_net = np.where(evening, net, net * 0.1)
        rows.append(pd.DataFrame({"timestamp": idx, "entity_id": e, "p_net_kw": p_net.astype("float32"),
                                  "bess_power_true_kw": np.float32(kw)}))
    pd.concat(rows).set_index(["timestamp", "entity_id"]).to_parquet(out / "agents_timeseries_2023_15min.parquet")

    prices = pd.DataFrame({"price_da_usd_mwh": np.where(evening, 50.0, 30.0),
                           "price_usd_mwh": np.where(evening, 60.0, 35.0)}, index=pd.Index(idx, name="timestamp"))
    prices.to_parquet(out / "system_prices_and_load_2023_15min.parquet")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    print("wrote", build(ap.parse_args().out))
