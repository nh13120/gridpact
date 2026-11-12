"""Real weather for the ENGIE agents' sites, from the free Open-Meteo archive (https://open-meteo.com, no key).

fetch() asks for hourly shortwave radiation (W/m2) at a latitude and longitude for a date range and caches the answer under
fixtures/weather/, so everything downstream runs offline after the first call. Only coordinates and dates are sent.
"""
import json
import urllib.request
from pathlib import Path

import pandas as pd

CACHE = Path(__file__).resolve().parent.parent / "fixtures" / "weather"
URL = ("https://archive-api.open-meteo.com/v1/archive?latitude={lat:.4f}&longitude={lon:.4f}&start_date={a}&end_date={b}"
       "&hourly=shortwave_radiation,cloud_cover,temperature_2m&timezone=America%2FChicago")


def fetch(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    """Hourly real weather, local (America/Chicago) time. Columns: ghi_wm2, cloud_pct, temp_c."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"om_{lat:.2f}_{lon:.2f}_{start}_{end}.json"
    if not path.exists():
        with urllib.request.urlopen(URL.format(lat=lat, lon=lon, a=start, b=end), timeout=90) as r:
            path.write_text(r.read().decode())
    h = json.loads(path.read_text())["hourly"]
    return pd.DataFrame({"ghi_wm2": h["shortwave_radiation"], "cloud_pct": h["cloud_cover"], "temp_c": h["temperature_2m"]},
                        index=pd.to_datetime(h["time"]))
