# Protocol behind the final evaluation decision

The protocol record explains why the submitted reference was retained. The
[original aggregate outcomes](../../reports/final_sprint_2026-09-30.json) are
unchanged; superseded variant catalogues and unfinished implementation plans are
not part of the maintained project.

## Population and alignment

**48 chronological ladder episodes** were split into 24 older development episodes
and 24 later holdout episodes. Both seats of a seed stayed together. The keeper had
to reproduce terminal rewards exactly before a recorded opponent replay could
support a counterfactual comparison. A recorded opponent tape cannot react to a
changed policy, so replay results are not a complete responsive-game evaluation.

The keeper's observed **18 wins / 10 ties / 20 losses** yield
`(18 + 0.5 * 10) / 48 = 47.9167%`. Official ladder rating and this local score are
separate quantities. The [findings](final_sprint_2026-09-30.md) explain the validation
mismatch and the final interpretation.

## Necessary selection controls

| Control | Recorded decision | Consequence |
|---|---|---|
| Matched fixed-policy comparisons | `NO_FIXED_POLICY_IMPROVEMENT` | Keep the reference; isolated rescued losses do not outweigh overall regression. |
| Keeper-centered boundary selection | `INNER_VALIDATION_REJECTED` | Hindsight opportunity did not validate an effective learned selector. |
| Forward-only boundary-rule evaluation | `ROLLING_CV_REJECTED` | The candidate failed without opening the latest holdout. |

The boundary study produced **1,084 accepted calibration/branch results**. Rolling
validation reused them with expanding windows: episodes 1–12 → 13–16,
1–16 → 17–20, and 1–20 → 21–24. It allowed at most one bounded intervention per game.
The registered gate required at least **+1.5** total validation score units, at least
one rescued loss, at most one sacrificed win, and no four-episode fold worse than
**−0.5**. The best rule families reached only **+0.5** and rescued no losses.

Earlier rejected screens and an interrupted native experiment remain recorded in
the original JSON. None is advertised as a final implemented replacement. An
execution failure is not a scientific rejection; no missing outcome is invented.

## Integrity and public replay

Source/engine identity, completed-game validity, and accepted-result fingerprints
were checked before reuse. A later failure did not justify recomputing accepted
games or relaxing a gate. One frozen nominee, rather than repeated holdout search,
was the permitted path to confirmation.

The [public reproduction guide](../REPRODUCIBILITY.md) uses repository-local
aggregate evidence and authored simulator inputs. It does not need the retired
AWS space or private policy. Run `scripts/verify_final_sprint.py` in the locked
environment to check the recorded decision arithmetic; the browser export auditor
separately validates the educational simulation.
