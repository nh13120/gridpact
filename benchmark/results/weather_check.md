# Does real weather explain what GridPact settles on?

Real weather: Open-Meteo archive at each plant's coordinates. ENGIE 2023 observed columns only.

| seller | corr(real sun, solar output), 2 summer weeks, hourly | corr(day's real sun, battery charge at 17:00), 365 days | R2 | days |
|---|---|---|---|---|
| PVB_37 | 0.94 | -0.03 | 0.001 | 365 |
| PVB_17 | 0.82 | 0.17 | 0.028 | 365 |
| PVB_32 | 0.88 | 0.27 | 0.07 | 365 |
| PVB_44 | 0.83 | 0.14 | 0.02 | 365 |

Reading: weather explains solar output well, and explains almost none of the evening battery charge (R2 under 0.1).
So it cannot independently check the evening energy a seller promises, and GridPact does not use it in settlement.
