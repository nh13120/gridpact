"""Concurrency regression: before the whole-tool locking, 300 agents registering from a thread pool crashed
the shared SQLite connection ("bad parameter or other API misuse"). benchmark.scale runs a full scripted day
with contended threads on a synthetic registry and prints a summary line."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_many_agents_at_once_keep_the_ledger_intact_and_catch_every_liar():
    out = subprocess.run([sys.executable, "-m", "benchmark.scale", "--sellers", "60", "--buyers", "30", "--auditors", "4",
                          "--workers", "16"], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-800:]
    m = re.search(r"commitments (\d+)\s+liar commitments (\d+)\s+valid challenges (\d+)\s+ledger intact: (\w+)", out.stdout)
    assert m, out.stdout
    commitments, liar_commitments, valid, intact = int(m[1]), int(m[2]), int(m[3]), m[4]
    assert commitments == 90 and liar_commitments > 0 and valid == liar_commitments and intact == "True"
