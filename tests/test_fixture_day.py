"""A whole GridPact day on the synthetic fixture (no sponsor data, no API key, no LLM).

Runs tests/scripted_day.py in a subprocess so the data directory is set before gridpact is imported.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_day(tmp_path, *args):
    env = {**os.environ, "GRIDPACT_DATA_DIR": str(ROOT / "fixtures" / "synthetic"),
           "GRIDPACT_DB": str(tmp_path / "day.db")}
    p = subprocess.run([sys.executable, "-m", "tests.scripted_day", *args], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_day_runs_end_to_end(tmp_path):
    out = run_day(tmp_path)
    assert out["ledger_ok"] is True
    assert out["challenge_valid"] is True                       # the 2x liar is caught
    assert out["commitments"] == {"PVB_17": 1, "PVB_37": 1}
    honest = out["settled"]["PVB_17"]
    assert honest["delivered"] == honest["committed"] == 6000.0 and honest["penalty"] == 0.0
    liar = out["settled"]["PVB_37"]
    assert liar["committed"] == 7500.0                           # trimmed to its real 2500 kW battery (v2)
    assert liar["delivered"] == liar["committed"]


def test_repeated_propose_is_not_deduplicated(tmp_path):
    """KNOWN GAP, recorded on purpose: a retried `propose` creates a second offer, and accepting both
    double-books the seller. Re-accepting the SAME offer is refused, but there is no request id.
    A client (for example the Nanda Town bridge) must deduplicate retries itself, or the server must
    gain an idempotency key. If that is fixed, flip this test."""
    out = run_day(tmp_path, "--repeat-propose")
    assert out["commitments"]["PVB_17"] == 2
    assert out["settled"]["PVB_17"]["committed"] == 12000.0      # twice the 6000 kWh the buyer asked for
