# GridPact benchmark (HW7)

Does GridPact's stake and auditor mechanism catch sellers that over-declare their capacity, without
punishing honest ones, and at what cost? This folder holds the preregistered plan, the harness, every
run log, and the results. Read `PREREGISTRATION.md` first: it fixed the claim, the baseline, the
metrics, the pass/fail thresholds and the case list before any run, and its Amendments section
records what changed afterwards and why.

## What was tested

One GridPact day per run: owners register agents (a liar's owner declares a capacity above the
battery's nameplate), Haiku 5.5 agents negotiate over MCP, an auditor agent reads the ledger and
challenges, then settlement runs. Two conditions share the same prompts, model, turn caps, scenarios
and seeds:

- `gridpact`: metered settlement, stake, auditor turn before settlement.
- `baseline`: the seller is paid for what it committed, as if every claim were true. No penalty, no auditor.

A third condition, `stake_only`, is derived from the gridpact runs by removing the auditor's effects.
It costs nothing to compute and answers what the LLM auditor adds beyond the stake.

Ground truth is the battery nameplate from the ENGIE metadata, checked once against the truth column
`bess_power_true_kw`. The scorer recomputes delivery from it and never reads what an agent said.
15 scenarios (9 tuning, 6 held-out with a different buyer, region, season and lie factors), 5 seeds
each, 150 runs. The held-out set was never used to choose anything.

## Results, v1 (`results/summary_v1.md`)

All six preregistered checks pass.

| check | gridpact | baseline |
|---|---|---|
| liars caught before settlement (P1) | 25/25 tuning, 25/25 held-out | none, by construction |
| honest sellers falsely challenged (P2) | 2/160 | 0 |
| buyer's loss to fraud, mean per run (P3) | -$538 (the buyer is paid penalties) | +$355 |
| what lying earned over honesty, mean (P4) | -$664 | +$355 |
| honest sellers that got a trade (P5) | 0.920 | 0.929 |
| $ per settled trade (P6) | $0.0016 | $0.0012 (gridpact is 1.37x) |

A run costs about half a cent and 25 to 35 seconds. The gridpact condition uses about 28% more
input tokens, almost all of it the auditor's ledger read.

Things the harder cases showed:

- The two false challenges were a rounding trap. The ledger prints `declared_flex_kw` to one decimal
  (6837.4) and the auditor's brief gave the nameplate as a whole number (6837). Twice, in the scenario
  with a 1.08x liar, the auditor read the 0.4 kW gap as a lie and lost the $50 bond.
- A 1.08x liar sits under the protocol's 1.10x tolerance. The auditor challenged it in 5 of 5 runs and
  lost the bond every time: its brief says "exceeds nameplate", the server's rule is 1.1x. Settlement
  still charged the 8% shortfall.
- Told it had a side deal with one liar, the auditor challenged that liar anyway, 5 of 5 runs. Haiku
  would not collude, the same way it refused to lie as a seller in HW6.
- An auditor limited to 2 turns still filed both challenges, because the SDK counts assistant
  messages and the model issues several tool calls per message.
- The `stake_only` rows show the same fraud loss as `gridpact`. For one day's money the LLM auditor is
  redundant: the stake does the work. What the auditor adds is the reputation cut, the cap reset,
  and (from v2) freeing the volume the liar could not deliver.

## Where it stops helping (`results/stress_v1.md`, `stress_v1.png`)

Sweeping the number of sellers from 2 to 16 with a quarter of them lying at 2x: recall stays 1.0,
no buyer or auditor ever hits its turn cap, and the ledger stays under one page. The limit is
elsewhere. From 6 sellers the declared caps exceed the buyer's need, so the buyer fills its 5,942
kWh/step on paper from the nearest four sellers, two of which have doubled caps, and never contacts
the rest. Real delivery is 65% of need at every n from 6 to 16, in both conditions. The share of
honest sellers that trade falls from 1.0 to 0.22. GridPact catches both liars and refunds the buyer,
but the energy outcome is identical to the baseline.

## The one change, and v2 (`results/compare_v1_v2.md`, `summary_v2.md`, `stress_v2.md`)

In v2 a valid challenge trims the liar's not-yet-settled commitments down to its real cap, releases
the stake on the cut, and the buyer gets one more round to re-source the released volume from
sellers it has not contracted. The expected effects were written down before running
(`PREREGISTRATION.md`, "Phase 3 decision"). Only the gridpact condition was rerun: the baseline has
no challenges, so nothing changes there.

Tuning, stress levels: delivery rose from 65% of need to 90% (n=6), 88% (n=8), 87% (n=12) and 81%
(n=16); honest sellers trading went from 0.50 to 1.00 at n=6 and 0.33 to 0.67 at n=8. The two
2-seller and 4-seller cases could not move (the buyer needs more than all sellers have) and did not.

Held-out: the one case with room to move, `double_sell_h`, went from the honest seller idle in 5 of 5
runs to trading in 5 of 5, with delivery 0.87 to 1.00. The other five held-out cases had no spare
sellers and stayed where they were, as predicted. P1 to P6 still pass; false challenges are now 0/160.

Two costs of the change, both visible only after running it:

- At 12 and 16 sellers the re-sourced volume sometimes reaches a liar further down the list, after
  the audit has already happened. That liar is never challenged. Recall in the stress sweep fell to
  0.8 (n=12) and 0.67 (n=16); it happened in 8 of those 10 runs. The stake still charges the shortfall,
  so the buyer is not out of pocket, but the challenge layer misses it. Fixing it means a second
  audit after re-sourcing, which is a second change and was not made.
- Trimming removes the shortfall, so the liar no longer pays penalties, only the bounty. Lying still
  earns less than honesty in every run, but the gap shrank from about -$600 to about -$100 per run.
  Runs cost 15% to 45% more because of the extra round.

Delivery does not reach 100% at n >= 6 even in v2. Several honest sellers hold less than 3 hours
of energy at nameplate, so they run dry late in the 12-step window. That is the simulator's truth,
not a lie, and the auditor cannot and should not challenge it.

## What we would claim

The preregistered claim holds in both versions: with the stake and auditor, every catchable liar
was caught before settlement, 2 of 160 honest sellers (0 in v2) were falsely challenged, the buyer
lost nothing to fraud and lying never paid; under trust settlement lying paid in every run. The
part of that claim that carries real uncertainty is the auditor's recall, and it was 1.0 on both the
tuning and the held-out cases; the money results are deterministic once the trades exist.

What the benchmark changed our minds about: catching a liar is not the hard part in this setting.
A fixed rule on two numbers does it, and the deterministic stake already makes lying unprofitable.
The hard part is that a lie distorts who gets to sell before anyone checks, and the v2 change
only partly repairs that, at the price of weaker deterrence and a new blind spot.

## Limitations

- Delivery is bounded by the registry nameplate, not measured from telemetry; the only lie the
  system supports is an inflated declared capacity. Lies in metered delivery are December work.
- The auditor is given the nameplates in its brief. It compares two numbers it is handed; the
  benchmark does not test an auditor that must find evidence.
- Haiku 5.5 only, default temperature (the SDK exposes none). "Seeds" are repetitions, so the
  spread across seeds is run-to-run variance of the model, not of the scenario.
- One buyer per market in most cases; the two-buyer cases are the only ones where sellers face
  competing demand.

## Reproduce

Commands and the exact scenario lists are in `PREREGISTRATION.md` section 10. Every table and plot
in `results/` is regenerated from `runs/` by `score.py`, `analyze.py`, `stress.py` and `compare.py`.
Total API spend for everything here was about $1.60 against a $15 cap.

## Independent replication (v1r, v2r)

On 2026-11-04 the whole benchmark was rerun from scratch with the live model: v1 from a checkout of tag
`v1` (`runs/v1r/`, 190 runs) and v2 from the v2 code (`runs/v2r/`, 85 runs), about $1.2, no failed runs.
Re-scoring the original logs reproduced every committed table exactly. Fresh runs: all preregistered checks
pass in both versions; liars caught 50/50; false challenges 0/160 (2/160 originally); fraud loss -$545 vs
-$538; v2 recall at 12 and 16 sellers 0.87 and 0.73 (0.80 and 0.67), so the blind spot reproduces. The v1
65% delivery plateau reproduced at 6 and 8 sellers but not fully at 12 and 16 (0.69, 0.88), so its size at
large n is noisy. Tables: `results/results_v1r.csv`, `results_v2r.csv`, `summary_v1r.md`, `summary_v2r.md`.
The original v1 and v2 results are unchanged and remain the numbers the report is based on.

## Report and contributions

The submitted PDF is `HW7_report.pdf` (written by Maheen from the files in this folder). Contributions:
Nicolas wrote the preregistration, harness, scorer, ran the 190 v1 and 85 v2 runs and made the v2 change;
Maheen wrote the report and, earlier, fixed the bounty accounting and added the money-conservation check and
settlement tests (`tests/test_settle.py`) that the deterministic settlement here relies on.

## Files

| path | what |
|---|---|
| `PREREGISTRATION.md` | claim, baseline, metrics, checks, cases, budget; Phase 3 decision; dated amendments |
| `scenarios.json` | the 15 scenarios and 4 stress levels |
| `run.py` | runs one day per (scenario, condition, seed), several in parallel, resumable |
| `score.py` | grades every run against ground truth; writes `results/results_<version>.csv` |
| `analyze.py` | tables and the P1 to P6 checks; writes `results/summary_<version>.md` |
| `stress.py` | the sweep table, hypothesis checks and plot |
| `compare.py` | before/after v1 vs v2, tuning and held-out separately |
| `runs/<version>/<run>/` | `transcript.jsonl` (every tool call and result) and `run.json` (ground truth, all tables, cost, tokens, time) |
