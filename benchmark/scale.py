"""How GridPact's own machinery behaves with hundreds of agents. NO LLM: scripted agents on a synthetic registry.

    python -m benchmark.scale --sellers 200 --buyers 100 --auditors 10 [--workers 32]

Builds a synthetic fixture with that many agents, then in one process: everyone registers, each buyer proposes to
three sellers, sellers accept, 20% of sellers over-declare 2x, auditors challenge every commitment of a liar,
the day settles. Agents act from a thread pool so the server's single write lock is really contended.
Prints seconds per phase, per-call latency, and checks the ledger hash chain and that every liar was caught.
It measures the server, not the language models: an LLM turn costs ~5 s (measured, results_v2.csv), so see the
README for the model-bound estimate.
"""
import argparse
import os
import random
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sellers", type=int, default=200); ap.add_argument("--buyers", type=int, default=100)
    ap.add_argument("--auditors", type=int, default=10); ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--liar-share", type=float, default=0.2); ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    tmp = Path(tempfile.mkdtemp())
    os.environ["GRIDPACT_DATA_DIR"] = str(tmp / "data"); os.environ["GRIDPACT_DB"] = str(tmp / "scale.db")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from gridpact import db, fixture, ledger, server, settle, data

    rnd = random.Random(a.seed)
    sellers = [f"PVB_{i:03d}" for i in range(a.sellers)]; buyers = [f"COM_{i:03d}" for i in range(a.buyers)]
    kw = {s: rnd.choice([2000.0, 2500.0, 3000.0, 5000.0]) for s in sellers}
    fixture.AGENTS = ([(b, "community", 1 + i % 9, 0.0, 0.0, -3000.0) for i, b in enumerate(buyers)] +
                      [(s, "pv_bess", 1 + i % 9, kw[s], kw[s] * 3, kw[s] * 0.8) for i, s in enumerate(sellers)])
    fixture.build(tmp / "data")
    liars = set(rnd.sample(sellers, int(a.sellers * a.liar_share)))
    db.reset()
    lat = {}
    pool = ThreadPoolExecutor(a.workers)

    def timed(name, fn, *args, **kw_):
        t = time.perf_counter(); r = fn(*args, **kw_); lat.setdefault(name, []).append(time.perf_counter() - t); return r

    def phase(name, jobs):
        t = time.perf_counter(); out = list(pool.map(lambda j: j(), jobs)); print(f"{name:<22}{time.perf_counter()-t:7.2f} s  ({len(jobs)} calls)"); return out

    reg = phase("register", [lambda s=s: timed("register", server.register_agent, s, "seller", kw[s] * 2 if s in liars else None) for s in sellers] +
                            [lambda b=b: timed("register", server.register_agent, b, "buyer") for b in buyers] +
                            [lambda i=i: timed("register", server.register_agent, f"AUD_{i:02d}", "auditor") for i in range(a.auditors)])
    assert all(r["ok"] for r in reg), [r for r in reg if not r["ok"]][:2]
    tok, capmap = {}, {}
    for r in reg: tok[r["agent_id"]] = r["token"]; capmap[r["agent_id"]] = r["trade_cap_kwh"]
    plan = [(b, s) for b in buyers for s in rnd.sample(sellers, 3)]
    def propose(b, s):
        cap = capmap[s]
        return timed("propose", server.propose, tok[b], s, 68, 79, min(50.0, cap / 3), 45.0, 60.0)
    offers = phase("propose", [lambda b=b, s=s: propose(b, s) for b, s in plan])
    ok_offers = [(o["offer_id"], s) for o, (b, s) in zip(offers, plan) if o.get("ok")]
    acc = phase("respond (accept)", [lambda o=o, s=s: timed("respond", server.respond, tok[s], o, "accept") for o, s in ok_offers])
    committed = [r for r in acc if r.get("ok")]
    cm = [dict(c) for c in server.conn_().execute("SELECT commitment_id, seller FROM commitments")]
    lie_c = [c for c in cm if c["seller"] in liars]
    ch = phase("challenge liars", [lambda c=c, i=i: timed("challenge", server.challenge, tok[f"AUD_{i % a.auditors:02d}"], c["commitment_id"],
                                                          "envelope exceeds nameplate", "scale test") for i, c in enumerate(lie_c)])
    valid = sum(r.get("verdict") == "valid" for r in ch)
    day = data.load_day("2023-06-19", sellers + buyers)
    t = time.perf_counter(); rows = settle.settle_day(server.conn_(), day); print(f"{'settle day':<22}{time.perf_counter()-t:7.2f} s  ({len(rows)} step rows)")
    ledger_ok = ledger.verify_chain(server.conn_()) is None
    print(f"\nagents {a.sellers + a.buyers + a.auditors}  offers {len(ok_offers)}  commitments {len(committed)}  liar commitments {len(lie_c)}  valid challenges {valid}  ledger intact: {ledger_ok}")
    print("per-call latency ms (p50 / p95 / max):")
    for k, v in lat.items():
        v = sorted(x * 1000 for x in v); print(f"  {k:<10}{statistics.median(v):7.1f} /{v[int(len(v)*.95)-1]:7.1f} /{v[-1]:7.1f}   n={len(v)}")


if __name__ == "__main__":
    main()
