# Review of supplied rounds 19 and 20

Source: `kaggriculture_service_value_results.zip`, supplied by the owner. All 39
manifest-listed file hashes match the supplied bytes. This analysis did not run
an agent, test suite, notebook, or account command.

| Measurement | Collection service (19) | Maintenance deadlines (20) |
|---|---:|---:|
| Archived observations | 957 | 957 |
| Worker–task rows | 19,393 | 16,571 |
| Changed observations | 355 | 2 |
| Passing tests reported | 64 | 64 |
| Failed / error / skipped tests | 0 / 0 / 0 | 0 / 0 / 0 |
| Installed mechanics cases reported | 20 | 80 |
| Screen seconds | 62.2401 | 60.1154 |
| Maximum candidate callback ms | 19.0587 | 20.4151 |
| Completed game pairs | 0 | 0 |
| Official submission score | Not available | Not available |

The collection changes split 120, 120, and 115 across the three source episodes.
The maintenance changes occur at step 594 in the two seat views of seed 1601;
seed 1602 has none. These are not two independent demonstrations of the maintenance
family. Collection activation is broad enough to justify a first paired outcome
experiment. Maintenance activation is rare and may not appear in a fresh game;
that itself must be reported rather than selecting a favorable seed afterward.

## Presentation qualification
Both archived notebooks have nine of ten code cells marked executed, with no saved
error outputs. The missing execution marker is a chart-display cell. The collection
notebook contains eight Plotly outputs; the maintenance notebook contains ten, but
that does not establish a clean full rerun of the latter. Do not rerun the expensive
screens merely to refresh presentation. Use the new reporting notebook or run only
the plotting cells on existing evidence and save.

## Methodological decision
Keep the two screened policies unchanged for their first preregistered block. The
new 12-per-family descriptors are outcome-blind context for interpretation, not
extra scoring changes. A full game gives local win/tie/loss and coin endpoints;
it is not a Kaggle leaderboard rating. One matched block remains exploratory.

## Account state
The user's preflight records local HEAD at
`7194116dfc92a8663139611233b5a221dad431a4` and ten verified restored objects. It
explicitly records `remote_head_verified: false`. No current GitHub visibility,
remote main, license, forks, account changes, or new merges were checked here.
