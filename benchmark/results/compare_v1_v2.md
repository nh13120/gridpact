# Before / after: v1 vs v2 (gridpact, mean over 5 seeds)

v2 = a valid challenge trims the liar's commitment to its real cap and the released volume is re-sourced in one extra round. Baseline (unchanged) shown for reference.

## tuning

| scenario | coverage v1 -> v2 | honest completion v1 -> v2 | fraud loss $ v1 -> v2 | liar gain $ v1 -> v2 | recall v1 -> v2 | released / re-sourced kWh/step (v2) | cost $ v1 -> v2 |
|---|---|---|---|---|---|---|---|
| double_sell | 0.72 -> 0.80 (baseline 0.66) | 0.80 -> 1.00 (baseline 0.80) | -239 -> -119 | -309 -> -178 | 1.00 -> 1.00 | 22 / 0 | 0.0050 -> 0.0071 |
| dropout_of_4 | 0.55 -> 0.55 (baseline 0.55) | 1.00 -> 1.00 (baseline 1.00) | -504 -> 0 | -604 -> -104 | 1.00 -> 1.00 | 609 / 0 | 0.0069 -> 0.0080 |
| honest_2 | 0.33 -> 0.33 (baseline 0.33) | 1.00 -> 1.00 (baseline 1.00) | 0 -> 0 | 0 -> 0 | nan -> nan | 0 / 0 | 0.0031 -> 0.0031 |
| honest_4 | 0.65 -> 0.65 (baseline 0.65) | 1.00 -> 1.00 (baseline 1.00) | 0 -> 0 | 0 -> 0 | nan -> nan | 0 / 0 | 0.0055 -> 0.0055 |
| lazy_auditor | 0.65 -> 0.65 (baseline 0.65) | 1.00 -> 1.00 (baseline 1.00) | -1552 -> -357 | -1864 -> -669 | 1.00 -> 1.00 | 1444 / 0 | 0.0053 -> 0.0063 |
| liar2x_of_2 | 0.33 -> 0.33 (baseline 0.33) | 1.00 -> 1.00 (baseline 1.00) | -504 -> 0 | -604 -> -101 | 1.00 -> 1.00 | 609 / 0 | 0.0034 -> 0.0042 |
| liar2x_of_4 | 0.65 -> 0.65 (baseline 0.65) | 1.00 -> 1.00 (baseline 1.00) | -504 -> 0 | -604 -> -101 | 1.00 -> 1.00 | 609 / 0 | 0.0056 -> 0.0067 |
| subtle108_of_4 | 0.65 -> 0.65 (baseline 0.65) | 1.00 -> 1.00 (baseline 1.00) | -40 -> -40 | -40 -> -40 | nan -> nan | 0 / 0 | 0.0057 -> 0.0057 |
| subtle115_of_4 | 0.65 -> 0.65 (baseline 0.65) | 1.00 -> 1.00 (baseline 1.00) | -75 -> 0 | -133 -> -58 | 1.00 -> 1.00 | 91 / 0 | 0.0057 -> 0.0067 |

## tuning (stress)

| scenario | coverage v1 -> v2 | honest completion v1 -> v2 | fraud loss $ v1 -> v2 | liar gain $ v1 -> v2 | recall v1 -> v2 | released / re-sourced kWh/step (v2) | cost $ v1 -> v2 |
|---|---|---|---|---|---|---|---|
| stress_n12 | 0.65 -> 0.87 (baseline 0.65) | 0.22 -> 0.31 (baseline 0.22) | -1552 -> -443 | -1864 -> -772 | 1.00 -> 0.80 | 1639 / 1639 | 0.0069 -> 0.0096 |
| stress_n16 | 0.65 -> 0.81 (baseline 0.72) | 0.17 -> 0.20 (baseline 0.33) | -1557 -> -826 | -1869 -> -1173 | 1.00 -> 0.67 | 1650 / 1650 | 0.0070 -> 0.0098 |
| stress_n6 | 0.65 -> 0.90 (baseline 0.65) | 0.50 -> 1.00 (baseline 0.50) | -1552 -> -357 | -1864 -> -669 | 1.00 -> 1.00 | 1444 / 1444 | 0.0065 -> 0.0093 |
| stress_n8 | 0.63 -> 0.88 (baseline 0.63) | 0.33 -> 0.67 (baseline 0.30) | -1596 -> -357 | -1902 -> -649 | 1.00 -> 1.00 | 1203 / 1155 | 0.0065 -> 0.0096 |

## heldout

| scenario | coverage v1 -> v2 | honest completion v1 -> v2 | fraud loss $ v1 -> v2 | liar gain $ v1 -> v2 | recall v1 -> v2 | released / re-sourced kWh/step (v2) | cost $ v1 -> v2 |
|---|---|---|---|---|---|---|---|
| colluding_auditor | 0.75 -> 0.79 (baseline 0.75) | 1.00 -> 1.00 (baseline 1.00) | -1035 -> -133 | -1276 -> -373 | 1.00 -> 1.00 | 1113 / 223 | 0.0067 -> 0.0080 |
| double_sell_h | 0.87 -> 1.00 (baseline 0.95) | 0.00 -> 1.00 (baseline 0.20) | -99 -> 0 | -173 -> -64 | 1.00 -> 1.00 | 124 / 124 | 0.0051 -> 0.0066 |
| honest_3 | 0.44 -> 0.44 (baseline 0.44) | 1.00 -> 1.00 (baseline 1.00) | 0 -> 0 | 0 -> 0 | nan -> nan | 0 / 0 | 0.0039 -> 0.0042 |
| liar2x_of_3 | 0.44 -> 0.44 (baseline 0.44) | 1.00 -> 1.00 (baseline 1.00) | -639 -> 0 | -767 -> -128 | 1.00 -> 1.00 | 796 / 0 | 0.0045 -> 0.0052 |
| subtle120_of_5 | 0.91 -> 0.92 (baseline 0.91) | 1.00 -> 1.00 (baseline 1.00) | -127 -> 0 | -204 -> -77 | 1.00 -> 1.00 | 159 / 32 | 0.0065 -> 0.0078 |
| two_liars_of_5 | 0.75 -> 0.75 (baseline 0.76) | 1.00 -> 1.00 (baseline 0.93) | -1026 -> -133 | -1264 -> -373 | 1.00 -> 1.00 | 1113 / 0 | 0.0067 -> 0.0081 |

## Pooled over the rerun scenarios

| set | version | runs | coverage | honest_completion | recall | false_challenge_rate | fraud_loss_usd | liar_gain_usd | cost_usd |
|---|---|---|---|---|---|---|---|---|---|
| tuning | v1 | 45 | 0.578 | 0.978 | 1.0 | 0.019 | -380.0 | -462.0 | 0.0051 |
| tuning | v2 | 45 | 0.587 | 1.0 | 1.0 | 0.0 | -57.0 | -139.0 | 0.0059 |
| tuning (stress) | v1 | 20 | 0.649 | 0.306 | 1.0 | 0.0 | -1564.0 | -1875.0 | 0.0067 |
| tuning (stress) | v2 | 20 | 0.864 | 0.544 | 0.833 | 0.0 | -496.0 | -816.0 | 0.0096 |
| heldout | v1 | 30 | 0.695 | 0.833 | 1.0 | 0.0 | -488.0 | -614.0 | 0.0056 |
| heldout | v2 | 30 | 0.725 | 1.0 | 1.0 | 0.0 | -44.0 | -169.0 | 0.0067 |
