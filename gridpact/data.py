"""Load one simulated day of ENGIE data for the demo agents.

Only *obs* columns are read here (what a real meter would show). The truth
columns (`anomaly_flag`, `*_true_*`) are reserved for verify.py.
Run `python -m gridpact.data` to print the chosen day.
"""
import pandas as pd

from gridpact.config import DATA_DIR, TZ

DAY = "2023-06-19"  # local date; chosen in docs/DATA_NOTES.md
AGENTS = {"COM_09": "buyer", "PVB_17": "honest_seller", "PVB_37": "liar"}
from gridpact.config import STEP_H  # noqa: E402  (one 15-minute step, in hours)

META_COLS = ["entity_id", "entity_type", "bus", "lat", "lon", "bess_power_kw",
             "bess_energy_kwh", "flex_up_kw", "flex_down_kw", "flex_duration_h"]


def load_metadata(agent_ids=tuple(AGENTS)):
    """Static facts per agent (bus, battery size, declared flexibility envelope)."""
    meta = pd.read_parquet(DATA_DIR / "agents_metadata.parquet", columns=META_COLS)
    return meta[meta.entity_id.isin(agent_ids)].set_index("entity_id")


def load_day(day=DAY, agent_ids=tuple(AGENTS)):
    """One row per (step, agent): step 0..95, surplus/deficit in kWh, prices in $/MWh.

    surplus_kwh = energy the agent exported in that step (p_net_kw > 0)
    deficit_kwh = energy it imported (p_net_kw < 0)
    """
    start_utc = pd.Timestamp(day, tz=TZ).tz_convert("UTC")
    end_utc = start_utc + pd.Timedelta(days=1)
    ts = pd.read_parquet(
        DATA_DIR / "agents_timeseries_2023_15min.parquet",
        columns=["p_net_kw"],
        filters=[("entity_id", "in", list(agent_ids)),
                 ("timestamp", ">=", start_utc), ("timestamp", "<", end_utc)],
    ).reset_index()
    prices = pd.read_parquet(DATA_DIR / "system_prices_and_load_2023_15min.parquet",
                             columns=["price_da_usd_mwh", "price_usd_mwh"])
    df = ts.merge(prices, left_on="timestamp", right_index=True)
    df["step"] = ((df.timestamp - start_utc) // pd.Timedelta("15min")).astype(int)
    df["surplus_kwh"] = df.p_net_kw.clip(lower=0) * STEP_H
    df["deficit_kwh"] = (-df.p_net_kw).clip(lower=0) * STEP_H
    cols = ["step", "timestamp", "entity_id", "surplus_kwh", "deficit_kwh",
            "price_da_usd_mwh", "price_usd_mwh"]
    return df[cols].sort_values(["step", "entity_id"]).reset_index(drop=True)


def evening(df):
    """Steps 68..79 = 17:00-19:45 local, the trading window for the demo."""
    return df[df.step.between(68, 79)]


if __name__ == "__main__":
    df = load_day()
    meta = load_metadata()
    print(f"Day {DAY} ({TZ}), {df.step.nunique()} steps, agents {list(AGENTS)}\n")
    summary = pd.DataFrame({
        "role": pd.Series(AGENTS),
        "bus": meta.bus,
        "flex_up_kw": meta.flex_up_kw.round(),
        "bess_kw": meta.bess_power_kw.round(),
        "day_surplus_kwh": df.groupby("entity_id").surplus_kwh.sum().round(),
        "day_deficit_kwh": df.groupby("entity_id").deficit_kwh.sum().round(),
        "evening_surplus_kwh": evening(df).groupby("entity_id").surplus_kwh.sum().round(),
        "evening_deficit_kwh": evening(df).groupby("entity_id").deficit_kwh.sum().round(),
    })
    print(summary.to_string())
    ev = evening(df).groupby("step")[["price_da_usd_mwh", "price_usd_mwh"]].first()
    print(f"\nEvening prices $/MWh: day-ahead {ev.price_da_usd_mwh.min():.0f}-{ev.price_da_usd_mwh.max():.0f}, "
          f"real-time {ev.price_usd_mwh.min():.0f}-{ev.price_usd_mwh.max():.0f}")
