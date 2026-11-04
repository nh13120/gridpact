# Results smoke

2 real runs (1 gridpact, 1 baseline); stake_only is derived from the gridpact runs. Model claude-haiku-5-5.

## Per condition and set (mean ± sd over scenarios x seeds)

| condition | set | runs | recall | false_challenge_rate | fraud_loss_usd | liar_gain_usd | honest_completion | buyer_paid_usd | wall_s | tokens_in | tokens_out | cost_usd | cost_per_commitment |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | tuning | 1 | 0 ± 0 | 0 ± 0 | 328 ± 0 | 328 ± 0 | 1 ± 0 | 1.39e+03 ± 0 | 15 ± 0 | 3.14e+04 ± 0 | 1.61e+03 ± 0 | 0.00224 ± 0 | 0.00112 ± 0 |
| gridpact | tuning | 1 | 1 ± 0 | 0 ± 0 | -504 ± 0 | -604 ± 0 | 1 ± 0 | 1.09e+03 ± 0 | 20.2 ± 0 | 4.51e+04 ± 0 | 2.27e+03 ± 0 | 0.00355 ± 0 | 0.00178 ± 0 |
| stake_only | tuning | 1 | 0 ± 0 | 0 ± 0 | -504 ± 0 | -504 ± 0 | 1 ± 0 | 1.09e+03 ± 0 | 20.2 ± 0 | 4.51e+04 ± 0 | 2.27e+03 ± 0 | 0.00355 ± 0 | 0.00178 ± 0 |

## Per scenario (mean over seeds)

| scenario | condition | recall | false_challenge_rate | fraud_loss_usd | liar_gain_usd | honest_completion | n_commitments | cost_usd |
|---|---|---|---|---|---|---|---|---|
| liar2x_of_2 | baseline | 0.0 | 0.0 | 328.5 | 328.5 | 1.0 | 2.0 | 0.002 |
| liar2x_of_2 | gridpact | 1.0 | 0.0 | -503.7 | -604.47 | 1.0 | 2.0 | 0.004 |
| liar2x_of_2 | stake_only | 0.0 | 0.0 | -503.7 | -503.7 | 1.0 | 2.0 | 0.004 |

## Preregistered checks

| check | result | numbers |
|---|---|---|
| P1 recall tuning >= 0.90 | PASS | 1/1 catchable liars caught = 1.000 |
| P1 recall heldout >= 0.90 | FAIL | 0/0 catchable liars caught = nan |
| P2 false challenges <= 0.05 | PASS | 0/1 honest sellers challenged = 0.000 |
| P3 fraud loss: gridpact <= 0 every run where the lie bit | PASS | 1/1 runs; mean $-504 |
| P3 fraud loss: baseline > 0 every run where the lie bit | PASS | 1/1 runs; mean $328 |
| P4 liar gain: gridpact < 0 every run where the lie bit | PASS | 1/1 runs; mean $-604 |
| P4 liar gain: baseline >= 0 every run where the lie bit | PASS | 1/1 runs; mean $328 |
| P5 honest completion gap <= 0.10 | PASS | gridpact 1.000 vs baseline 1.000 |
| P6 $ per settled commitment <= 2x | PASS | gridpact $0.0018 vs baseline $0.0011 = 1.58x |

Integrity: ledger ok True, settlement = truth True, audit before settlement True, dropout ok True. Gridpact runs with a liar whose lie never bit (committed <= real capacity): 0.
