# Notebook 15: verified results and the missing comparison

Source: the user-uploaded `kaggriculture_crop_lifecycle_results.zip`. All 30 manifest-listed hashes were checked. Its notebook has 10 executed code cells and zero error outputs. These are source-derived results, not new notebook-16 outcomes.

| Arm | Own coins | Opponent coins | Margin | Local match score |
|---|---:|---:|---:|---:|
| Control | 44,840 | 44,082 | 758 | 1 |
| Retire WATER on empty exhausted crops | 41,510 | 41,240 | 270 | 1 |
| Retirement plus early clearing | 43,451 | 41,639 | 1,812 | 1 |

Retirement versus control: own cash −3,330; margin −488. Combined renewal versus control: own cash −1,389; margin +1,054. Both failed the registered conservative requirement that own cash, margin and match score must not decline. They should not be automatically promoted. However, “both are competitively worse” is not established: combined renewal improved margin and kept the win. The cash veto is a research safeguard, not the competition's ranking formula.

The added clearing rule under retirement increased own cash by 1,941 and margin by 1,542. That is the observed `renew − retire` contrast, not the effect of clearing with ordinary watering. That latter cell was never run. The difference between these two clearing effects is also unknown.

The screen processed 372 observations, 2,855 plant rows, 384 artificial component checks and 52 tests. It found seven sampled callbacks with changes in at least one candidate. Screening took 21.677 seconds; the three-arm continuation took 73.051 seconds. Maximum reported candidate callbacks were 86.506 ms in screening and 151.840 ms in the pilot. These are reported wall-clock measurements on the user's machine, not estimates for another run.

All three prior branches contain 527 consecutive suffix records with matching starting-state hashes. Control has 526 recorded next-state reproduction checks. All endpoint residual-product counts are zero. Requested WATER commands were 185 / 155 / 196 for control / retirement / combined renewal. Requested commands are not evidence that every command succeeded.

## Interpretation, separated from the source

The working hypothesis for notebook 16 is that the effect of early clearing depends on which competing WATER jobs remain eligible. It is not yet proven. No additional model or priority tuning is justified from these outcomes alone. Complete the missing factorial cell and then stop within-block tuning: promising changes need new seed groups and different opponents, and a valid submission score is needed for any leaderboard comparison.

No raw episode payloads were included in this results ZIP. Their integrity will be checked on AWS before using them. No official submission score or independent validation is present.
