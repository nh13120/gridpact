# Results v2r

150 real runs (75 gridpact, 75 baseline); stake_only is derived from the gridpact runs. Model claude-haiku-5-5.

## Per condition and set (mean ± sd over scenarios x seeds)

| condition | set | runs | recall | false_challenge_rate | fraud_loss_usd | liar_gain_usd | honest_completion | buyer_paid_usd | wall_s | tokens_in | tokens_out | cost_usd | cost_per_commitment |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | heldout | 30 | 0.000 ± 0.000 | 0.000 ± 0.000 | 319 ± 289 | 319 ± 289 | 0.856 ± 0.347 | 2,240 ± 1,044 | 28 ± 5 | 53,664 ± 10,275 | 3,157 ± 659 | 0.004 ± 0.001 | 0.001 ± 0.000 |
| baseline | tuning | 45 | 0.000 ± 0.000 | 0.000 ± 0.000 | 245 ± 312 | 245 ± 312 | 0.978 ± 0.149 | 2,080 ± 807 | 25 ± 6 | 48,591 ± 10,393 | 2,883 ± 717 | 0.004 ± 0.001 | 0.001 ± 0.000 |
| gridpact | heldout | 30 | 1.000 ± 0.000 | 0.000 ± 0.000 | -44 ± 64 | -170 ± 151 | 1.000 ± 0.000 | 1,981 ± 949 | 37 ± 9 | 78,630 ± 18,638 | 4,996 ± 1,362 | 0.005 ± 0.001 | 0.001 ± 0.000 |
| gridpact | tuning | 45 | 1.000 ± 0.000 | 0.000 ± 0.000 | -51 ± 114 | -130 ± 199 | 1.000 ± 0.000 | 1,613 ± 548 | 32 ± 7 | 65,365 ± 14,584 | 4,227 ± 1,053 | 0.004 ± 0.001 | 0.001 ± 0.000 |
| stake_only | heldout | 30 | 0.000 ± 0.000 | 0.000 ± 0.000 | -44 ± 64 | -44 ± 64 | 1.000 ± 0.000 | 1,981 ± 949 | 37 ± 9 | 78,630 ± 18,638 | 4,996 ± 1,362 | 0.005 ± 0.001 | 0.001 ± 0.000 |
| stake_only | tuning | 45 | 0.000 ± 0.000 | 0.000 ± 0.000 | -51 ± 114 | -51 ± 114 | 1.000 ± 0.000 | 1,613 ± 548 | 32 ± 7 | 65,365 ± 14,584 | 4,227 ± 1,053 | 0.004 ± 0.001 | 0.001 ± 0.000 |

## Per scenario (mean over seeds)

| scenario | condition | recall | false_challenge_rate | fraud_loss_usd | liar_gain_usd | honest_completion | n_commitments | cost_usd |
|---|---|---|---|---|---|---|---|---|
| colluding_auditor | baseline | 0.0 | 0.0 | 689.14 | 689.14 | 1.0 | 5.0 | 0.005 |
| colluding_auditor | gridpact | 1.0 | 0.0 | -132.89 | -373.334 | 1.0 | 5.8 | 0.006 |
| colluding_auditor | stake_only | 0.0 | 0.0 | -132.89 | -132.89 | 1.0 | 5.8 | 0.006 |
| double_sell | baseline | 0.0 | 0.0 | 133.08 | 133.08 | 0.8 | 2.8 | 0.004 |
| double_sell | gridpact | 1.0 | 0.0 | -59.64 | -98.758 | 1.0 | 3.0 | 0.004 |
| double_sell | stake_only | 0.0 | 0.0 | -59.64 | -59.64 | 1.0 | 3.0 | 0.004 |
| double_sell_h | baseline | 0.0 | 0.0 | 65.138 | 65.138 | 0.2 | 2.2 | 0.004 |
| double_sell_h | gridpact | 1.0 | 0.0 | 0.0 | -64.492 | 1.0 | 3.2 | 0.006 |
| double_sell_h | stake_only | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 3.2 | 0.006 |
| dropout_of_4 | baseline | 0.0 | 0.0 | 328.5 | 328.5 | 1.0 | 3.0 | 0.005 |
| dropout_of_4 | gridpact | 1.0 | 0.0 | 0.0 | -102.522 | 1.0 | 3.0 | 0.006 |
| dropout_of_4 | stake_only | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 3.0 | 0.006 |
| honest_2 | baseline | nan | 0.0 | 0.0 | 0.0 | 1.0 | 2.0 | 0.002 |
| honest_2 | gridpact | nan | 0.0 | 0.0 | 0.0 | 1.0 | 2.0 | 0.003 |
| honest_2 | stake_only | nan | 0.0 | 0.0 | 0.0 | 1.0 | 2.0 | 0.003 |
| honest_3 | baseline | nan | 0.0 | 0.0 | 0.0 | 1.0 | 3.0 | 0.003 |
| honest_3 | gridpact | nan | 0.0 | 0.0 | 0.0 | 1.0 | 3.0 | 0.003 |
| honest_3 | stake_only | nan | 0.0 | 0.0 | 0.0 | 1.0 | 3.0 | 0.003 |
| honest_4 | baseline | nan | 0.0 | 0.0 | 0.0 | 1.0 | 4.0 | 0.004 |
| honest_4 | gridpact | nan | 0.0 | 0.0 | 0.0 | 1.0 | 4.0 | 0.005 |
| honest_4 | stake_only | nan | 0.0 | 0.0 | 0.0 | 1.0 | 4.0 | 0.005 |
| lazy_auditor | baseline | 0.0 | 0.0 | 1012.4 | 1012.4 | 1.0 | 4.0 | 0.004 |
| lazy_auditor | gridpact | 1.0 | 0.0 | -357.27 | -668.68 | 1.0 | 4.0 | 0.004 |
| lazy_auditor | stake_only | 0.0 | 0.0 | -357.27 | -357.27 | 1.0 | 4.0 | 0.004 |
| liar2x_of_2 | baseline | 0.0 | 0.0 | 328.5 | 328.5 | 1.0 | 2.0 | 0.002 |
| liar2x_of_2 | gridpact | 1.0 | 0.0 | 0.0 | -100.77 | 1.0 | 2.0 | 0.003 |
| liar2x_of_2 | stake_only | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 2.0 | 0.003 |
| liar2x_of_3 | baseline | 0.0 | 0.0 | 419.954 | 419.954 | 1.0 | 3.0 | 0.003 |
| liar2x_of_3 | gridpact | 1.0 | 0.0 | 0.0 | -129.064 | 1.0 | 3.0 | 0.004 |
| liar2x_of_3 | stake_only | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 3.0 | 0.004 |
| liar2x_of_4 | baseline | 0.0 | 0.0 | 324.12 | 324.12 | 1.0 | 4.0 | 0.004 |
| liar2x_of_4 | gridpact | 1.0 | 0.0 | 0.0 | -102.522 | 1.0 | 4.0 | 0.005 |
| liar2x_of_4 | stake_only | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 4.0 | 0.005 |
| subtle108_of_4 | baseline | nan | 0.0 | 26.1 | 26.1 | 1.0 | 4.0 | 0.004 |
| subtle108_of_4 | gridpact | nan | 0.0 | -40.02 | -40.02 | 1.0 | 4.0 | 0.004 |
| subtle108_of_4 | stake_only | nan | 0.0 | -40.02 | -40.02 | 1.0 | 4.0 | 0.004 |
| subtle115_of_4 | baseline | 0.0 | 0.0 | 48.78 | 48.78 | 1.0 | 4.0 | 0.004 |
| subtle115_of_4 | gridpact | 1.0 | 0.0 | 0.0 | -59.892 | 1.0 | 4.0 | 0.005 |
| subtle115_of_4 | stake_only | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 4.0 | 0.005 |
| subtle120_of_5 | baseline | 0.0 | 0.0 | 83.618 | 83.618 | 1.0 | 5.0 | 0.005 |
| subtle120_of_5 | gridpact | 1.0 | 0.0 | 0.0 | -77.388 | 1.0 | 5.0 | 0.006 |
| subtle120_of_5 | stake_only | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 5.0 | 0.006 |
| two_liars_of_5 | baseline | 0.0 | 0.0 | 658.512 | 658.512 | 0.933 | 4.8 | 0.005 |
| two_liars_of_5 | gridpact | 1.0 | 0.0 | -132.89 | -373.334 | 1.0 | 5.4 | 0.006 |
| two_liars_of_5 | stake_only | 0.0 | 0.0 | -132.89 | -132.89 | 1.0 | 5.4 | 0.006 |

## Preregistered checks

| check | result | numbers |
|---|---|---|
| P1 recall tuning >= 0.90 | PASS | 25/25 catchable liars caught = 1.000 |
| P1 recall heldout >= 0.90 | PASS | 25/25 catchable liars caught = 1.000 |
| P2 false challenges <= 0.05 | PASS | 0/160 honest sellers challenged = 0.000 |
| P3 fraud loss: gridpact <= 0 every run where the lie bit | PASS | 57/57 runs; mean $-63 |
| P3 fraud loss: baseline > 0 every run where the lie bit | PASS | 58/58 runs; mean $355 |
| P4 liar gain: gridpact < 0 every run where the lie bit | PASS | 57/57 runs; mean $-191 |
| P4 liar gain: baseline >= 0 every run where the lie bit | PASS | 58/58 runs; mean $355 |
| P5 honest completion gap <= 0.10 | PASS | gridpact 1.000 vs baseline 0.929 |
| P6 $ per settled commitment <= 2x | PASS | gridpact $0.0013 vs baseline $0.0012 = 1.14x |

Integrity: ledger ok True, settlement = truth True, audit before settlement True, dropout ok True. Gridpact runs with a liar whose lie never bit (committed <= real capacity): 3.

Sub-tolerance liars (factor <= 1.10): 5 runs, challenged in 5 (ruled invalid by design), shortfall still penalised by settlement in all.

## Failure scenarios (excluded from P1)

| scenario | recall | n_caught | n_catchable | false_challenge_rate | cost_usd |
|---|---|---|---|---|---|
| colluding_auditor | 1.0 | 2.0 | 2.0 | 0.0 | 0.006 |
| lazy_auditor | 1.0 | 2.0 | 2.0 | 0.0 | 0.004 |
