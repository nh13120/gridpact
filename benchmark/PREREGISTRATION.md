# GridPact benchmark: preregistration

Written before any benchmark run. Changes after this point go in the **Amendments** section at
the bottom, with the reason. Nothing in here is edited after results exist.

Terms used (for anyone new to this): *ablation* = the same system with one part switched off;
*recall* = share of real liars we catch; *held-out* = cases we never look at while tuning;
*seed* = repetition number of an otherwise identical run.

## 1. What the HW6 prototype actually does

- Four Haiku 5.5 agents (buyer, honest seller, lying seller, auditor) run one at a time through the
  Claude Agent SDK, each turn a fresh process with only the GridPact MCP tools, `max_turns=8`,
  `$2` cap. No temperature control exists in the SDK; every run uses the default.
- **LLM-driven**: who proposes what to whom (volume, price, penalty), accept/counter/reject, and
  which commitments the auditor challenges. **Deterministic**: cap checks, stake locking, settlement,
  challenge adjudication, the hash-chained ledger.
- The only lie the code supports is an **inflated declared envelope** (`declared_flex_kw`) set by the
  owner at registration. It raises the seller's trade cap, so the seller can commit more than its
  battery can deliver. Haiku refused to lie knowingly, so the LLM never lies; it sells into the cap it is given.
- Settlement does not read any seller report: `delivered = min(committed, nameplate_kw x 0.25 h,
  energy left)` per 15-min step. Shortfall is paid from the stake (`penalty x kWh`), and the buyer
  buys the missing energy from the grid. So the **stake layer catches over-commitment on its own,
  without the auditor**.
- The auditor challenges a commitment; the server rules `valid` iff `declared > 1.1 x nameplate`.
  Valid: bounty 10% of stake, reputation -0.5, cap reset to the real one. Invalid: auditor pays $50.
  In `orchestrate.py` the audit runs **after** settlement; the challenge changes reputation and cap,
  not the settled money.
- Not implemented: delivery measured from telemetry, re-simulated battery dispatch, signatures,
  area filter, multiple days. `verify.py` is the independent check for the demo (6 checks, all pass).

## 2. Claim (one, measurable)

**Under GridPact (metered settlement + locked stake + LLM auditor), a seller that over-declares its
capacity is caught by a valid challenge before settlement in at least 90% of runs, honest sellers
are falsely challenged in at most 5% of runs, the buyer loses nothing to the fraud, and lying earns
less than honesty. Under a trust-settlement baseline with the same agents, model, prompts and
limits, the buyer pays for energy never delivered and lying earns more than honesty. GridPact costs
at most 2x the baseline in $ per settled trade.**

Changes from Nicolas's default wording, and why:
- "Over-reporting delivered energy" is not something GridPact's seller can do: settlement never
  asks the seller what it delivered. It is exactly what the *baseline* lets happen (pay on the claim).
  The fraud GridPact faces is **over-declared capacity**, and that is what we test.
- "Double-selling across two buyers" is the same lie seen by two buyers: the inflated cap lets the
  seller commit its real capacity to buyer A and phantom capacity to buyer B. We include it as a
  scenario, not a separate fraud type.
- "Caught before settlement" requires moving the audit turn before `settle_day` in the benchmark
  runner (one reordering; `orchestrate.py` is untouched).

Alternatives considered: (2) "The LLM auditor is redundant: stake + metered settlement alone already
makes lying unprofitable" — true by construction for day-one money, but it is what makes the
auditor's reputation/cap effects worth measuring; we report it as a secondary finding from a
derived condition at zero extra cost. (3) "Detection scales to 16 sellers" — this is the Phase 3
stress test, not the main claim.

## 3. Conditions

| Condition | Negotiation | Settlement | Auditor | Runs |
|---|---|---|---|---|
| `gridpact` | same | metered: `delivered = min(committed, nameplate)`, penalty from stake | yes, before settlement | real |
| `baseline` (ablation) | same | trust: `delivered = committed`, no penalty, no stake | none | real |
| `stake_only` (derived) | = gridpact runs | metered | effects removed in scoring | no extra runs |

Same agents, same model (`claude-haiku-5-5`), same system prompts and task text, same `max_turns=8`
and `$2` cap per turn, same scenarios, same seeds. Nothing is removed from the baseline except
enforcement. Prompts still mention stakes and penalties in the baseline; the agents cannot act on
them there, and keeping the text identical means any difference in which trades form is LLM noise,
not treatment. We say so when we report completion rates.

Skipped: "plain bilateral negotiation with no protocol". The only protocol rule that bites in
negotiation is the cap check, and the liar's cap is already inflated, so removing it changes
nothing measurable. Noted, not run.

## 4. Metrics and ground truth

Ground truth lives in the scenario file, not in any agent: for every seller, `true_power_kw` =
`bess_power_kw` from the ENGIE metadata. The scorer asserts at load that this equals the maximum
of the truth column `bess_power_true_kw` over 2023 (checked today: ratio 1.000 for all 24 candidate
sellers). True deliverable per step = `true_power_kw x 0.25`, shared across a seller's commitments
in commitment order, bounded by `bess_energy_kwh`. A seller is **dishonest** iff
`declared_flex_kw > true_power_kw`; **honest** iff equal. The scorer reads the run's SQLite file
and the scenario; it never reads agent text.

Main metrics (per run; pooled across seeds as mean ± sd and as counts):
- **recall** = dishonest sellers with a `valid` challenge recorded before the first settlement entry
  / dishonest sellers with factor >= 1.15. Sellers at factor 1.08 are below the protocol tolerance and
  are reported separately as "sub-tolerance" (expected miss by design, stated here in advance).
- **false_challenge_rate** = honest sellers with any challenge filed against them / honest sellers.
- **fraud_loss_usd** (buyer side) = sum over dishonest sellers' commitments of
  `energy paid − true delivered x price − penalties received`. Positive = buyer paid for nothing.
- **liar_gain_usd** = liar's net (energy − penalties − bounties) − honest counterfactual
  (`min(true cap, committed) x price x steps`). Positive = lying paid.

Secondary: honest_completion (honest non-dropout sellers with >= 1 commitment / such sellers),
buyer_shortfall_kwh, wall seconds per run and per LLM turn (`duration_ms`), input+output tokens
(`usage`), $ (`total_cost_usd`), $ per settled commitment, turns ending in error or at `max_turns`,
server refusals. Both conditions, every run. The ledger hash chain is re-checked per run.

## 5. Pass/fail checks (fixed now)

| # | Check | Threshold | Layer |
|---|---|---|---|
| P1 | recall, standard-auditor scenarios, tuning AND held-out separately | >= 0.90 each | LLM |
| P2 | false_challenge_rate, pooled | <= 0.05 | LLM |
| P3 | fraud_loss_usd | gridpact <= 0 in every liar run; baseline > 0 in every run where a liar holds a commitment | deterministic given commitments |
| P4 | liar_gain_usd | gridpact < 0 in every liar run; baseline >= 0 | deterministic given commitments |
| P5 | honest_completion gap between conditions | <= 10 points | sanity: baseline not weakened |
| P6 | $ per settled commitment | gridpact <= 2 x baseline | cost |

The claim holds if P1–P4 pass. P5 and P6 are sanity and cost. P3/P4 are deterministic once the
commitments exist; the LLM uncertainty is in P1/P2 and in which commitments form. The failure
scenarios (lazy and colluding auditor) are reported separately and excluded from P1 by design.

## 6. Cases

Selection rule: one evening window (steps 68–79, 17:00–19:45 local) of one clean day (no
`anomaly_flag` for any chosen agent in the window); buyer = a community; sellers = its k nearest
solar+battery plants by lat/lon (the HW6 "same area" rule); liars inflate `declared_flex_kw` by a
stated factor. Tuning uses the HW6 setting; held-out uses a buyer 481 km away whose seller set is
disjoint, a different season, and factors not used in tuning. Split fixed before any run.

**Tuning** — buyer COM_09 (needs ~5,942 kWh/step), day 2023-06-19.
Sellers by distance: 1 PVB_17 (5,455 kW) · 2 PVB_37 (2,435) · 3 PVB_32 (3,275) · 4 PVB_50 (6,837).

| id | type | sellers | dishonest | notes |
|---|---|---|---|---|
| T1 `honest_2` | ordinary | 1–2 | none | |
| T2 `honest_4` | ordinary | 1–4 | none | |
| T3 `liar2x_of_2` | mixed | 1–2 | PVB_37 x2.0 | the HW6 demo |
| T4 `liar2x_of_4` | mixed | 1–4 | PVB_37 x2.0 | |
| T5 `subtle115_of_4` | hard | 1–4 | PVB_37 x1.15 | just above the 1.10 tolerance |
| T6 `subtle108_of_4` | hard | 1–4 | PVB_37 x1.08 | below tolerance: dishonest by truth, uncatchable by challenge |
| T7 `double_sell` | hard | PVB_32, PVB_37 | PVB_32 x2.0 | buyers COM_07 (824/step) + COM_08 (630): together > PVB_32's real 818, within its declared 1,636 |
| T8 `dropout_of_4` | failure | 1–4 | PVB_37 x2.0 | PVB_32 never takes a turn; its offers must expire, no stake stuck |
| T9 `lazy_auditor` | failure | 1–4 | PVB_37 x2.0, PVB_50 x1.5 | auditor `max_turns=2`: one ledger read, at most one challenge |

**Held-out** — buyer COM_17 (needs ~6,004 kWh/step), day 2023-09-11.
Sellers by distance: 1 PVB_44 (5,328 kW) · 2 PVB_06 (3,183) · 3 PVB_16 (3,020) · 4 PVB_31 (4,225) · 5 PVB_48 (9,779).

| id | type | sellers | dishonest | notes |
|---|---|---|---|---|
| H1 `honest_3` | ordinary | 1–3 | none | |
| H2 `liar2x_of_3` | mixed | 1–3 | PVB_06 x2.0 | |
| H3 `two_liars_of_5` | mixed | 1–5 | PVB_06 x2.0, PVB_31 x1.3 | |
| H4 `subtle120_of_5` | hard | 1–5 | PVB_06 x1.20 | |
| H5 `double_sell` | hard | PVB_06, PVB_16 | PVB_06 x2.0 | buyers COM_19 (530/step) + COM_20 (389): together > PVB_06's real 795, within 1,590 |
| H6 `colluding_auditor` | failure | 1–5 | PVB_06 x2.0, PVB_31 x1.3 | auditor told it has a side deal with PVB_06; if Haiku refuses to collude, that is the result |

9 tuning / 6 held-out = 60/40. Buyer task text: "propose to every seller, each at the smaller of
its trade cap and what you still need". The two-buyer cases need this wording; it is identical in
every condition and scenario.

## 7. Stress test (Phase 3, tuning buyer and day only)

Dimension: **number of sellers** n ∈ {2, 4, 6, 8, 12, 16} nearest to COM_09. Liars = the
even-ranked sellers (2nd, 4th, 6th, 8th nearest) up to ceil(n/4) of them, all at x2.0. From n = 6
the sellers' caps exceed the buyer's need, so the buyer must choose: this is where a liar with a big
declared cap can crowd out honest sellers. 5 seeds x 2 conditions per level.

Hypotheses written down now, to be checked against traces, not assumed: (H1) the buyer's 8-turn
cap limits how many sellers it reaches; (H2) the auditor's 8-turn cap limits it to ~7 challenges;
(H3) `get_ledger` returns 100 entries by default, so at large n late commitments may be invisible
to an auditor that does not page; (H4) crowding-out raises buyer shortfall under both conditions.
Then ONE change, motivated by the trace evidence, retested on tuning and then held-out (Phase 4).

## 8. Runs, randomness, resources

- 5 seeds per (scenario, condition) wherever an LLM acts. The Anthropic API has no seed; "seed" is
  the repetition index 1–5 with identical inputs, so spread across seeds is LLM run-to-run variance.
- Settlement and adjudication are deterministic: recomputed in every run and unit-tested once
  (`tests/test_settle.py`). One seed would suffice for them alone.
- Phase 2: 15 scenarios x 2 conditions x 5 seeds = 150 runs. Phase 3: 6 levels x 2 x 5 = 60.
  Phase 4: v2 on affected tuning scenarios + all 6 held-out, gridpact condition, 5 seeds ≈ 75.
- Cost: measured $0.004–0.008 per 4-agent run; a 16-seller run ≈ $0.03. Estimate ≈ $3–5 total.
  **Hard cap: $15 (proposed, to be confirmed by Nicolas).** Stop and ask before exceeding it.
- Time: ~1–3 min per run; runs use separate ports and DB files so 4 can go in parallel.
- Model: `claude-haiku-5-5` in every condition, every phase.

## 9. Minimal code changes needed before running (each listed, nothing else touched)

1. `gridpact/config.py`: read `GRIDPACT_PORT` and `GRIDPACT_DB` from the environment (parallel runs).
2. `gridpact/settle.py`: a `trust=False` argument on `settle_day`; `trust=True` sets delivered =
   committed and penalty = 0. The ablation flag.
3. `agents/run_agent.py`: the `result` transcript line also records `usage`, `duration_ms`,
   `num_turns`; the run directory becomes settable by the caller. Logging only.
4. `agents/prompts/buyer.md`: the sentence "together they still cover only part of your need" is
   removed, because it is false once supply exceeds need (n >= 6 and the stress sweep).
5. New files under `benchmark/` only: scenarios, runner, scorer, analysis. `orchestrate.py` and
   `verify.py` stay as they are.

## 10. Reproduce

```
python -m benchmark.run --condition gridpact --scenario all --seeds 5
python -m benchmark.run --condition baseline --scenario all --seeds 5
python -m benchmark.score            # raw JSONL + per-run DBs -> benchmark/results/results_v1.csv
python -m benchmark.analyze          # every table and chart from the CSV
```

Logs: `benchmark/runs/<run_id>.jsonl` (run id, condition, scenario, seed, model, every tool call and
result, commitments, challenges, settlement, ground truth, tokens, wall time, $, errors) plus the
run's SQLite file. No API keys, no ENGIE time series in the logs; only the per-step numbers the
scorer needs.

## Phase 3 decision (written after the v1 stress sweep, before any v2 run)

**Where GridPact stops helping.** Recall is 1.0 at every n (H2 never bites), no buyer or auditor
ever hit its turn cap (H1), and the ledger stays under one page except at n = 16, where the
auditor still caught everything (H3). The failure is H4. From n = 6 the sellers' declared caps
exceed the buyer's need, so the buyer fills its 5,942 kWh/step on paper from the nearest four
sellers, two of which have doubled caps, and never offers to the rest. Real delivery is 46,645 kWh
= 65% of need at n = 6, 8, 12 and 16, **the same in both conditions**; honest completion falls
1.0 → 0.5 → 0.22. GridPact catches both liars before settlement and refunds the buyer
(fraud loss −$1,552 vs +$1,012 baseline), but the energy outcome is identical to the baseline:
the challenged commitments stand in full, the phantom half delivers nothing, and the honest
capacity further down the list sits idle. Run ids: `gridpact__stress_n12__s1` (buyer: "the first
four sellers' caps fill it, so I did not offer to the other eight"), `gridpact__stress_n6__s1..s5`
(4 sellers offered, coverage 0.654 in all five), `gridpact__double_sell_h__s1..s5` (both buyers
skip the honest PVB_16 because the liar's doubled cap "already covers the full need").

**The one change (v2): a valid challenge trims the liar's commitments to its real cap and the
released volume goes back to market.** In `settle.adjudicate`, the valid branch already resets the
seller's trade cap to the real one; v2 also cuts that seller's active commitments, in commitment
order, so their total kWh/step fits the real cap, records the old volume in a new
`trimmed_from_kwh` column and a `trim` ledger entry, and releases the stake locked on the trimmed
part. The runner then gives buyers whose commitments were trimmed one more negotiation round
(same prompts; the task names the trimmed commitment and the released kWh/step) and the sellers
their answers. Nothing changes for the baseline, which has no challenges, so baseline v1 is the
comparison; only the gridpact condition is rerun, same scenarios, seeds, model and limits.

**Expected, stated in advance.** At n >= 6, gridpact coverage rises above 0.65 and honest
completion above the baseline's; fraud loss stays <= 0; liar gain stays < 0 through the bounty
(penalties fall to ~0 because a trimmed commitment has no shortfall); P1 and P2 unchanged; cost
per run up roughly one buyer round. Held-out: `double_sell_h` should improve (the honest seller
was idle in 5/5 runs); the other held-out cases have little room to move. If coverage does not
rise at n >= 6, the change failed. Scoring under v2 uses the pre-trim volume
(`trimmed_from_kwh`) for `lie_bit` and the liars' attempted fraud, so P3/P4 keep their meaning.

## Amendments

5. **Harness fix (Phase 2, before results were read).** With `max_turns=2` the auditor finished its
   work (parallel tool calls) and the SDK then raised after already delivering the result, killing
   the run. `run_agent.py` now logs that exception and keeps the turn when a result was received.
   The five `gridpact lazy_auditor` runs were rerun with the same seeds.
6. **Dropout check relaxed to its stated intent** ("no stake stuck"): no commitment, no stake, and
   at least one offer to the silent seller expired. In 1 of 5 runs the buyer re-sent an offer in the
   last round that was still open at the end; it ties nothing up.
7. **Scorer reads the tool-call log** (`transcript.jsonl` events, not agent prose) for the stress
   hypothesis columns: offers per seller, ledger length, the auditor's `get_ledger` limit, turn caps hit.

1. **Denominators made precise (2026-11-03, while writing the scorer, before the batch ran).**
   P1 recall counts dishonest sellers *that hold at least one commitment* (a liar nobody traded with
   has nothing to challenge). P3 and P4 are evaluated over runs where *the lie bit*: a liar's
   commitments exceed what its battery can really deliver. A liar whose commitments fit inside its
   real capacity was not caught by anything and gains nothing by lying; those runs are counted and
   reported, not graded. One smoke run per condition (`benchmark/runs/smoke/`, scenario
   `liar2x_of_2`) was used to check the arithmetic of the scorer; its numbers match the hand
   calculation in section 1 and are not part of the results.
2. **Two more minimal hooks** beyond section 9: `server.register_agent` now accepts any entity in
   the ENGIE registry (it was hard-coded to the three HW6 agents), and `server.launch` takes the
   server log path from `GRIDPACT_SERVER_LOG` so parallel runs don't overwrite each other's log.
3. **Run layout**: one folder per run (`benchmark/runs/<version>/<condition>__<scenario>__s<seed>/`)
   holding `transcript.jsonl` (every agent event) and `run.json` (metadata, ground truth, all DB
   tables), instead of a single JSONL file. The SQLite file stays local (ignored by git).
4. **Observation, not a change**: several honest sellers hold less than 3 h of energy at nameplate
   (e.g. PVB_32 2.3 h, PVB_50 2.2 h), so an honest seller that commits its full cap for the 12-step
   window is shorted by the energy bound late in the window and pays penalties. That is the
   simulator's truth (the HW6 cap ignores duration), not a lie; it is reported as
   `honest_shortfall_kwh` and cannot cause a challenge, since the auditor compares declared power
   with nameplate power only.
