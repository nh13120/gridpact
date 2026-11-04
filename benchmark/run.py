"""Benchmark runner: one GridPact day per (scenario, condition, seed), several side by side.

    python -m benchmark.run --condition gridpact --scenario all --seeds 5 [--parallel 4] [--version v1]
    python -m benchmark.run --condition baseline --scenario liar2x_of_2 --seeds 1

The parent process only dispatches. Each run is a child process (`--one`) with its own port, SQLite
file and folder under benchmark/runs/<version>/<condition>__<scenario>__s<seed>/, because
gridpact.config reads GRIDPACT_DB and GRIDPACT_PORT once, at import. A finished run has a run.json;
runs that already have one are skipped, so a crashed batch can simply be started again.

Conditions:  gridpact = metered settlement + stake + auditor turn before settlement
             baseline = trust settlement (pay on the claim), no penalty drawn, no auditor
Same prompts, model, turn caps and task text in both; only enforcement differs.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUNS = HERE / "runs"
MODEL = "claude-haiku-5-5"
STEP_FROM, STEP_TO = 68, 79          # 17:00-19:45 local, as in HW6
MAX_ROUNDS = 4
BUDGET_CAP_USD = 15.0                # PREREGISTRATION.md section 8; the parent stops dispatching above it
BASE_PORT = 8800


def scenarios():
    return {s["id"]: s for s in json.loads((HERE / "scenarios.json").read_text())["scenarios"]}


# ----------------------------------------------------------------------------- one run (child)

def run_one(sc, condition, seed, rundir):
    # Imported here, after the parent set GRIDPACT_DB / GRIDPACT_PORT for this process.
    from gridpact import data, db, server, settle
    from gridpact.config import GRID_FEE_USD_MWH, STEP_H
    from agents import run_agent

    run_agent.RUN_DIR = rundir                      # transcript.jsonl lands in this run's folder
    buyers, sellers, dropouts = sc["buyers"], sc["sellers"], set(sc["dropouts"])
    ids = buyers + list(sellers)
    t0 = time.time()
    db.reset()
    proc = server.launch()
    try:
        day = data.load_day(sc["day"], ids)
        meta = data.load_metadata(ids)
        window = day[day.step.between(STEP_FROM, STEP_TO)]
        need = {b: float(window[window.entity_id == b].deficit_kwh.mean()) for b in buyers}
        da = float(window.price_da_usd_mwh.mean())
        grid = da + GRID_FEE_USD_MWH
        facts = (f"Trading window: steps {STEP_FROM} to {STEP_TO} (17:00-19:45 local, 12 steps). "
                 f"Day-ahead wholesale price {da:.0f} $/MWh; grid import price {grid:.0f} $/MWh.")

        # --- owners register (the lie, if any, is the inflated declared envelope) ----------------
        for b in buyers:
            assert server.register_agent(b, "buyer")["ok"]
        for s, factor in sellers.items():
            flex = factor * float(meta.loc[s].flex_up_kw) if factor != 1.0 else None   # None = registry value
            r = server.register_agent(s, "seller", flex)
            assert r["ok"], r
        if condition == "gridpact":
            assert server.register_agent("AUD_01", "auditor")["ok"]
        server._conn.close(); server._conn = None

        def q(sql, *a):
            c = db.connect(); rows = c.execute(sql, a).fetchall(); c.close(); return rows
        token = lambda a: q("SELECT token FROM agents WHERE agent_id = ?", a)[0]["token"]
        open_to = lambda a: q("SELECT 1 FROM offers WHERE to_agent = ? AND status = 'open'", a)
        committed = lambda s: q("SELECT 1 FROM commitments WHERE seller = ?", s)

        # --- day-ahead negotiation ---------------------------------------------------------------
        for rnd in range(1, MAX_ROUNDS + 1):
            server.set_round(rnd)
            for b in buyers:
                if rnd == 1:
                    task = (f"You are {b}, token {token(b)}. Find counterparties and propose a trade to every "
                            f"seller for the full window, each at the smaller of its trade cap (kWh per step) and "
                            f"what you still need. You need about {need[b]:.0f} kWh per step in total. {facts}")
                else:
                    task = (f"You are {b}, token {token(b)}. Round {rnd}. Check your inbox: accept counters at or "
                            f"below the grid price, otherwise counter. If a seller rejected and has no commitment "
                            f"with you yet, propose again at a better price. {facts}")
                run_agent.run(b, "buyer.md", task)
            for s, factor in sellers.items():
                if s in dropouts or not open_to(s):
                    continue
                m = meta.loc[s]
                if factor == 1.0:
                    role_file, envelope = "honest_seller.md", (
                        f"Your declared envelope is {m.flex_up_kw:.0f} kW, which is your true battery power.")
                else:   # the LLM is not asked to lie; it sells into the cap its owner registered (DECISIONS.md)
                    role_file, envelope = "liar.md", (
                        f"Your registered trade cap is {math.floor(factor * m.flex_up_kw * STEP_H)} kWh per step.")
                task = (f"You are {s}, token {token(s)}. Round {rnd}. {envelope} Check your inbox and answer "
                        f"every open offer. Your minimum price is {da:.0f} $/MWh (wholesale). {facts}")
                run_agent.run(s, role_file, task)
            no_open = not q("SELECT 1 FROM offers WHERE status = 'open'")
            all_committed = all(committed(s) for s in sellers if s not in dropouts)
            if no_open and (all_committed or rnd >= 2):
                break

        # --- audit BEFORE settlement (gridpact only) ---------------------------------------------
        if condition == "gridpact":
            nameplates = ", ".join(f"{s} {meta.loc[s].bess_power_kw:.0f} kW" for s in sellers)
            task = (f"You are AUD_01, token {token('AUD_01')}. Public registry, battery nameplate power: "
                    f"{nameplates}. Read the ledger. For each seller, compare declared_flex_kw in its register "
                    f"entry with its nameplate. Challenge each commitment of any seller whose declared envelope "
                    f"exceeds its nameplate (claim 'envelope exceeds nameplate', evidence with both numbers). "
                    f"Do not challenge the others.{sc['auditor']['extra']}")
            run_agent.run("AUD_01", "auditor.md", task, max_turns=sc["auditor"]["max_turns"])

        # --- v2: re-source the volume a valid challenge released (one extra round) ---------------
        resource_round = None
        trimmed = q("SELECT c.*, o.round_opened FROM commitments c JOIN offers o USING (offer_id) "
                    "WHERE trimmed_from_kwh IS NOT NULL")
        if trimmed:
            resource_round = rnd + 1
            server.set_round(resource_round)
            for b in buyers:
                mine = [c for c in trimmed if c["buyer"] == b]
                if not mine:
                    continue
                gap = sum(c["trimmed_from_kwh"] - c["kwh_per_step"] for c in mine)
                cuts = "; ".join(f"commitment #{c['commitment_id']} with {c['seller']} was cut from "
                                 f"{c['trimmed_from_kwh']:.0f} to {c['kwh_per_step']:.0f} kWh/step" for c in mine)
                task = (f"You are {b}, token {token(b)}. Round {resource_round}. An auditor's challenge was upheld: {cuts}. "
                        f"You still need about {gap:.0f} kWh per step more. Find counterparties and propose the "
                        f"missing volume to sellers you have no commitment with yet, each at the smaller of its trade "
                        f"cap and what you still need. {facts}")
                run_agent.run(b, "buyer.md", task)
            for s, factor in sellers.items():
                if s in dropouts or not open_to(s):
                    continue
                m = meta.loc[s]
                role_file, envelope = ("honest_seller.md", f"Your declared envelope is {m.flex_up_kw:.0f} kW, which is your true battery power.") \
                    if factor == 1.0 else ("liar.md", f"Your registered trade cap is {math.floor(factor * m.flex_up_kw * STEP_H)} kWh per step.")
                task = (f"You are {s}, token {token(s)}. Round {resource_round}. {envelope} Check your inbox and answer "
                        f"every open offer. Your minimum price is {da:.0f} $/MWh (wholesale). {facts}")
                run_agent.run(s, role_file, task)
            for b in buyers:                                     # accept any counters
                if open_to(b):
                    run_agent.run(b, "buyer.md", f"You are {b}, token {token(b)}. Round {resource_round}. Check your inbox: "
                                                 f"accept counters at or below the grid price, otherwise counter. {facts}")

        # --- settlement: metered (gridpact) or trust (baseline) ----------------------------------
        c = db.connect()
        settle.settle_day(c, day, trust=(condition == "baseline"))
        tables = {t: [dict(r) for r in c.execute(f"SELECT * FROM {t}")]
                  for t in ("agents", "offers", "commitments", "settlements", "challenges", "ledger")}
        c.close()
        for a in tables["agents"]:
            a.pop("token")                               # never log secrets
    finally:
        proc.terminate()

    # --- per-turn numbers from the transcript -------------------------------------------------
    turns = [json.loads(l) for l in (rundir / "transcript.jsonl").read_text().splitlines()]
    results = [t for t in turns if t["event"] == "result"]
    usage = lambda k: sum((t.get("usage") or {}).get(k, 0) for t in results)
    out = {
        "run_id": rundir.name, "version": rundir.parent.name, "condition": condition, "scenario": sc["id"],
        "set": sc["set"], "type": sc["type"], "seed": seed, "model": MODEL, "day": sc["day"],
        "window": [STEP_FROM, STEP_TO], "max_turns": 8, "auditor_max_turns": sc["auditor"]["max_turns"],
        "ground_truth": {s: {"factor": f, "true_power_kw": float(meta.loc[s].bess_power_kw),
                             "true_energy_kwh": float(meta.loc[s].bess_energy_kwh)} for s, f in sellers.items()},
        "buyers": buyers, "dropouts": sorted(dropouts), "need_kwh_per_step": need,
        "price_da": da, "price_grid": grid, "rt_price_by_step": {int(s): float(p) for s, p in
                                                                 day.groupby("step").price_usd_mwh.first().items()},
        "wall_s": round(time.time() - t0, 1), "rounds": rnd, "resource_round": resource_round,
        "llm_turns": len(results), "error_turns": sum(t["subtype"] != "success" for t in results),
        "api_turns": sum(t.get("num_turns") or 0 for t in results),
        "turn_ms": [t.get("duration_ms") for t in results],
        "tokens_in": usage("input_tokens") + usage("cache_read_input_tokens") + usage("cache_creation_input_tokens"),
        "tokens_out": usage("output_tokens"),
        "cost_usd": round(sum(t["cost_usd"] for t in results), 5),
        "tool_calls": sum(t["event"] == "tool_call" for t in turns),
        "refusals": sum(t["event"] == "tool_result" and '"ok": false' in t["text"] for t in turns),
        "tables": tables,
    }
    (rundir / "run.json").write_text(json.dumps(out, indent=1, default=str))
    return out


# ----------------------------------------------------------------------------- dispatch (parent)

def spent_so_far():
    return sum(json.loads(p.read_text())["cost_usd"] for p in RUNS.glob("*/*/run.json"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", choices=["gridpact", "baseline", "both"], default="both")
    ap.add_argument("--scenario", default="all", help="scenario id, 'all', 'tuning' or 'heldout'")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--version", default="v1")
    ap.add_argument("--one", nargs=3, metavar=("SCENARIO", "CONDITION", "SEED"), help="internal: run one in this process")
    args = ap.parse_args()
    scs = scenarios()

    if args.one:
        sid, cond, seed = args.one
        rundir = RUNS / args.version / f"{cond}__{sid}__s{seed}"
        out = run_one(scs[sid], cond, int(seed), rundir)
        print(f"DONE {out['run_id']} ${out['cost_usd']:.4f} commitments={len(out['tables']['commitments'])} "
              f"challenges={len(out['tables']['challenges'])} wall={out['wall_s']}s")
        return

    sel = args.scenario.split(",")                       # ids, sets ('tuning', 'heldout', 'stress') or 'all'
    wanted = [s for s in scs.values() if "all" in sel or s["set"] in sel or s["id"] in sel]
    conds = ["gridpact", "baseline"] if args.condition == "both" else [args.condition]
    jobs = [(s["id"], c, k) for s in wanted for c in conds for k in range(1, args.seeds + 1)]
    jobs = [j for j in jobs if not (RUNS / args.version / f"{j[1]}__{j[0]}__s{j[2]}" / "run.json").exists()]
    print(f"{len(jobs)} runs to do, ${spent_so_far():.2f} spent so far (cap ${BUDGET_CAP_USD})")

    running = {}                                  # slot -> (Popen, job)
    while jobs or running:
        while jobs and len(running) < args.parallel:
            if spent_so_far() >= BUDGET_CAP_USD:
                print("BUDGET CAP REACHED, not dispatching more"); jobs = []; break
            slot = next(i for i in range(args.parallel) if i not in running)
            sid, cond, seed = job = jobs.pop(0)
            rundir = RUNS / args.version / f"{cond}__{sid}__s{seed}"
            rundir.mkdir(parents=True, exist_ok=True)
            env = {**os.environ, "GRIDPACT_PORT": str(BASE_PORT + slot), "GRIDPACT_DB": str(rundir / "gridpact.db"),
                   "GRIDPACT_SERVER_LOG": str(rundir / "server.log")}
            p = subprocess.Popen([sys.executable, "-m", "benchmark.run", "--version", args.version,
                                  "--one", sid, cond, str(seed)], cwd=ROOT, env=env,
                                 stdout=open(rundir / "stdout.log", "w"), stderr=subprocess.STDOUT)
            running[slot] = (p, job)
        for slot, (p, job) in list(running.items()):
            if p.poll() is not None:
                del running[slot]
                rundir = RUNS / args.version / f"{job[1]}__{job[0]}__s{job[2]}"
                ok = (rundir / "run.json").exists()
                tail = (rundir / "stdout.log").read_text().strip().splitlines()[-1:] if ok else ["see stdout.log"]
                print(f"[{'ok' if ok else 'FAILED'}] {tail[0] if tail else ''}  ({len(jobs)} left)", flush=True)
        time.sleep(2)
    print(f"all done, ${spent_so_far():.2f} spent in total")


if __name__ == "__main__":
    main()
