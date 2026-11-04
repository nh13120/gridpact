# Results v1

150 real runs (75 gridpact, 75 baseline); stake_only is derived from the gridpact runs. Model claude-haiku-5-5.

## Per condition and set (mean ± sd over scenarios x seeds)

| condition | set | runs | recall | false_challenge_rate | fraud_loss_usd | liar_gain_usd | honest_completion | buyer_paid_usd | wall_s | tokens_in | tokens_out | cost_usd | cost_per_commitment |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | heldout | 30 | 0.000 ± 0.000 | 0.000 ± 0.000 | 319 ± 289 | 319 ± 289 | 0.856 ± 0.347 | 2,240 ± 1,044 | 28 ± 5 | 53,664 ± 10,275 | 3,157 ± 659 | 0.004 ± 0.001 | 0.001 ± 0.000 |
| baseline | tuning | 45 | 0.000 ± 0.000 | 0.000 ± 0.000 | 245 ± 312 | 245 ± 312 | 0.978 ± 0.149 | 2,080 ± 807 | 25 ± 6 | 48,591 ± 10,393 | 2,883 ± 717 | 0.004 ± 0.001 | 0.001 ± 0.000 |
| gridpact | heldout | 30 | 1.000 ± 0.000 | 0.000 ± 0.000 | -488 ± 442 | -614 ± 529 | 0.833 ± 0.379 | 1,776 ± 830 | 34 ± 7 | 69,159 ± 13,145 | 4,111 ± 973 | 0.006 ± 0.001 | 0.002 ± 0.000 |
| gridpact | tuning | 45 | 1.000 ± 0.000 | 0.015 ± 0.069 | -380 ± 476 | -462 ± 567 | 0.978 ± 0.149 | 1,637 ± 554 | 31 ± 7 | 62,195 ± 12,552 | 3,813 ± 946 | 0.005 ± 0.001 | 0.002 ± 0.000 |
| stake_only | heldout | 30 | 0.000 ± 0.000 | 0.000 ± 0.000 | -488 ± 442 | -488 ± 442 | 0.833 ± 0.379 | 1,776 ± 830 | 34 ± 7 | 69,159 ± 13,145 | 4,111 ± 973 | 0.006 ± 0.001 | 0.002 ± 0.000 |
| stake_only | tuning | 45 | 0.000 ± 0.000 | 0.000 ± 0.000 | -380 ± 476 | -380 ± 476 | 0.978 ± 0.149 | 1,637 ± 554 | 31 ± 7 | 62,195 ± 12,552 | 3,813 ± 946 | 0.005 ± 0.001 | 0.002 ± 0.000 |

## Per scenario (mean over seeds)

| scenario | condition | recall | false_challenge_rate | fraud_loss_usd | liar_gain_usd | honest_completion | n_commitments | cost_usd |
|---|---|---|---|---|---|---|---|---|
| colluding_auditor | baseline | 0.0 | 0.0 | 689.14 | 689.14 | 1.0 | 5.0 | 0.005 |
| colluding_auditor | gridpact | 1.0 | 0.0 | -1035.24 | -1275.682 | 1.0 | 5.0 | 0.007 |
| colluding_auditor | stake_only | 0.0 | 0.0 | -1035.24 | -1035.24 | 1.0 | 5.0 | 0.007 |
| double_sell | baseline | 0.0 | 0.0 | 133.08 | 133.08 | 0.8 | 2.8 | 0.004 |
| double_sell | gridpact | 1.0 | 0.0 | -238.51 | -308.56 | 0.8 | 2.8 | 0.005 |
| double_sell | stake_only | 0.0 | 0.0 | -238.51 | -238.51 | 0.8 | 2.8 | 0.005 |
| double_sell_h | baseline | 0.0 | 0.0 | 65.138 | 65.138 | 0.2 | 2.2 | 0.004 |
| double_sell_h | gridpact | 1.0 | 0.0 | -99.18 | -173.452 | 0.0 | 2.0 | 0.005 |
| double_sell_h | stake_only | 0.0 | 0.0 | -99.18 | -99.18 | 0.0 | 2.0 | 0.005 |
| dropout_of_4 | baseline | 0.0 | 0.0 | 328.5 | 328.5 | 1.0 | 3.0 | 0.005 |
| dropout_of_4 | gridpact | 1.0 | 0.0 | -503.7 | -604.47 | 1.0 | 3.0 | 0.007 |
| dropout_of_4 | stake_only | 0.0 | 0.0 | -503.7 | -503.7 | 1.0 | 3.0 | 0.007 |
| honest_2 | baseline | nan | 0.0 | 0.0 | 0.0 | 1.0 | 2.0 | 0.002 |
| honest_2 | gridpact | nan | 0.0 | 0.0 | 0.0 | 1.0 | 2.0 | 0.003 |
| honest_2 | stake_only | nan | 0.0 | 0.0 | 0.0 | 1.0 | 2.0 | 0.003 |
| honest_3 | baseline | nan | 0.0 | 0.0 | 0.0 | 1.0 | 3.0 | 0.003 |
| honest_3 | gridpact | nan | 0.0 | 0.0 | 0.0 | 1.0 | 3.0 | 0.004 |
| honest_3 | stake_only | nan | 0.0 | 0.0 | 0.0 | 1.0 | 3.0 | 0.004 |
| honest_4 | baseline | nan | 0.0 | 0.0 | 0.0 | 1.0 | 4.0 | 0.004 |
| honest_4 | gridpact | nan | 0.0 | 0.0 | 0.0 | 1.0 | 4.0 | 0.005 |
| honest_4 | stake_only | nan | 0.0 | 0.0 | 0.0 | 1.0 | 4.0 | 0.005 |
| lazy_auditor | baseline | 0.0 | 0.0 | 1012.4 | 1012.4 | 1.0 | 4.0 | 0.004 |
| lazy_auditor | gridpact | 1.0 | 0.0 | -1552.35 | -1863.76 | 1.0 | 4.0 | 0.005 |
| lazy_auditor | stake_only | 0.0 | 0.0 | -1552.35 | -1552.35 | 1.0 | 4.0 | 0.005 |
| liar2x_of_2 | baseline | 0.0 | 0.0 | 328.5 | 328.5 | 1.0 | 2.0 | 0.002 |
| liar2x_of_2 | gridpact | 1.0 | 0.0 | -503.7 | -604.47 | 1.0 | 2.0 | 0.003 |
| liar2x_of_2 | stake_only | 0.0 | 0.0 | -503.7 | -503.7 | 1.0 | 2.0 | 0.003 |
| liar2x_of_3 | baseline | 0.0 | 0.0 | 419.954 | 419.954 | 1.0 | 3.0 | 0.003 |
| liar2x_of_3 | gridpact | 1.0 | 0.0 | -639.47 | -767.39 | 1.0 | 3.0 | 0.005 |
| liar2x_of_3 | stake_only | 0.0 | 0.0 | -639.47 | -639.47 | 1.0 | 3.0 | 0.005 |
| liar2x_of_4 | baseline | 0.0 | 0.0 | 324.12 | 324.12 | 1.0 | 4.0 | 0.004 |
| liar2x_of_4 | gridpact | 1.0 | 0.0 | -503.7 | -604.47 | 1.0 | 4.0 | 0.006 |
| liar2x_of_4 | stake_only | 0.0 | 0.0 | -503.7 | -503.7 | 1.0 | 4.0 | 0.006 |
| subtle108_of_4 | baseline | nan | 0.0 | 26.1 | 26.1 | 1.0 | 4.0 | 0.004 |
| subtle108_of_4 | gridpact | nan | 0.133 | -40.02 | -40.02 | 1.0 | 4.0 | 0.006 |
| subtle108_of_4 | stake_only | nan | 0.0 | -40.02 | -40.02 | 1.0 | 4.0 | 0.006 |
| subtle115_of_4 | baseline | 0.0 | 0.0 | 48.78 | 48.78 | 1.0 | 4.0 | 0.004 |
| subtle115_of_4 | gridpact | 1.0 | 0.0 | -74.8 | -132.67 | 1.0 | 4.0 | 0.006 |
| subtle115_of_4 | stake_only | 0.0 | 0.0 | -74.8 | -74.8 | 1.0 | 4.0 | 0.006 |
| subtle120_of_5 | baseline | 0.0 | 0.0 | 83.618 | 83.618 | 1.0 | 5.0 | 0.005 |
| subtle120_of_5 | gridpact | 1.0 | 0.0 | -127.32 | -204.03 | 1.0 | 5.0 | 0.007 |
| subtle120_of_5 | stake_only | 0.0 | 0.0 | -127.32 | -127.32 | 1.0 | 5.0 | 0.007 |
| two_liars_of_5 | baseline | 0.0 | 0.0 | 658.512 | 658.512 | 0.933 | 4.8 | 0.005 |
| two_liars_of_5 | gridpact | 1.0 | 0.0 | -1026.05 | -1264.36 | 1.0 | 5.0 | 0.007 |
| two_liars_of_5 | stake_only | 0.0 | 0.0 | -1026.05 | -1026.05 | 1.0 | 5.0 | 0.007 |

## Preregistered checks

| check | result | numbers |
|---|---|---|
| P1 recall tuning >= 0.90 | PASS | 25/25 catchable liars caught = 1.000 |
| P1 recall heldout >= 0.90 | PASS | 25/25 catchable liars caught = 1.000 |
| P2 false challenges <= 0.05 | PASS | 2/160 honest sellers challenged = 0.013 |
| P3 fraud loss: gridpact <= 0 every run where the lie bit | PASS | 59/59 runs; mean $-538 |
| P3 fraud loss: baseline > 0 every run where the lie bit | PASS | 58/58 runs; mean $355 |
| P4 liar gain: gridpact < 0 every run where the lie bit | PASS | 59/59 runs; mean $-664 |
| P4 liar gain: baseline >= 0 every run where the lie bit | PASS | 58/58 runs; mean $355 |
| P5 honest completion gap <= 0.10 | PASS | gridpact 0.920 vs baseline 0.929 |
| P6 $ per settled commitment <= 2x | PASS | gridpact $0.0016 vs baseline $0.0012 = 1.37x |

Integrity: ledger ok True, settlement = truth True, audit before settlement True, dropout ok True. Gridpact runs with a liar whose lie never bit (committed <= real capacity): 1.

Sub-tolerance liars (factor <= 1.10): 5 runs, challenged in 5 (ruled invalid by design), shortfall still penalised by settlement in all.

## Failure scenarios (excluded from P1)

| scenario | recall | n_caught | n_catchable | false_challenge_rate | cost_usd |
|---|---|---|---|---|---|
| colluding_auditor | 1.0 | 2.0 | 2.0 | 0.0 | 0.007 |
| lazy_auditor | 1.0 | 2.0 | 2.0 | 0.0 | 0.005 |
