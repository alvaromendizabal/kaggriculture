# Leading-solution reproduction matrix

| Reference / mechanism | Status | Evidence / decision |
|---|---|---|
| Current Tetsutani timing reference | **Reference integrated; upstream optimizer not recreated** | strong local confirmation; latest live snapshot did not beat older submission |
| Boatlee V16-RC5 | **Exact reference reproduced and rejected** | 0/32 versus each current live source |
| Farm2945 | **Fixed opponent; optimizer not recreated** | earlier benchmark coverage |
| `farming_v50` | **Fixed opponent** | field coverage |
| `market_shock` | **Fixed opponent** | field coverage |
| Route bank R100/R106/R107/R110 | **Recreated, screened, rejected** | OOF gains did not transfer |
| Service-route synthesis | **Recreated, validated, rejected** | 64-game score 0.65625 failed gate |
| Multiday crop programs | **Recreated, rejected** | field score delta -0.1667 |
| Adjacent-sale action value | **Trained on recent data; rejected** | holdout gates failed |
| Recent Sep 21-22 top-route families | **Not yet implemented** | highest-priority ceiling-escape item |
| Broad current-meta veto league | **Incomplete** | next milestone expands validation |
| Whole-task-graph value/search | **Not yet implemented** | follow-on after stronger route baseline |

Inspecting a public notebook or using it as an opponent is not counted as recreating its optimization process.
