# Progress

Check the phase's "done when" command before ticking it. Details in `PLAN.md`.

- [x] Phase 0 - repo setup + data inspection. Check: `python -m gridpact.data`
- [x] Phase 1 - SQLite state + hash-chained ledger. Check: `pytest tests/test_ledger.py`
- [x] Phase 2 - MCP server with 7 tools. Check: `python -m tests.smoke_client`
- [x] Phase 3 - LLM agents + orchestration. Check: `python orchestrate.py --demo` (needs ANTHROPIC_API_KEY; ~$0.01)
- [x] Phase 4 - settlement + challenge adjudication. Check: `python orchestrate.py --demo` (liar: shortfall, valid challenge, reputation 0.5)
- [x] Phase 5 - independent `verify.py` + `python orchestrate.py --demo` (6/6 checks)
- [x] Phase 6 - README complete, code review fixes, fresh-clone test; GitHub repo pending approval

## Benchmark (HW7): `benchmark/PREREGISTRATION.md` is the spec, `benchmark/results/` the output

- [x] B1 - preregistration committed before any run (`preregistration` commit)
- [x] B2 - harness + 150 runs (15 scenarios x 2 conditions x 5 seeds): `python -m benchmark.score && python -m benchmark.analyze` -> `results/results_v1.csv`, `summary_v1.md`. P1-P6 all pass.
- [x] B3 - stress sweep 2 -> 16 sellers (40 more runs): `python -m benchmark.stress` -> `results/stress_v1.md`, `stress_v1.png`. Limit found at n >= 6 (crowding out); change decided (see PREREGISTRATION "Phase 3 decision").
- [x] B4 - v2 change (challenge trims the commitment, released volume re-sourced), 85 gridpact reruns on tuning then held-out: `python -m benchmark.compare` -> `results/compare_v1_v2.md`; `results_v2.csv`, `summary_v2.md`, `stress_v2.md`. Write-up in `benchmark/README.md`. Git tags `v1` (before) and `v2` (after).

## What's next
Read `benchmark/README.md`. Open question for the next iteration: a second audit after re-sourcing (recall fell at 12-16 sellers in v2). December work after that (see README "Next steps").

- [x] HW9: agent guide, cold-start test (3 runs), get_commitments, boundary and regression tests, final slides and report (`coldstart/report/`)
