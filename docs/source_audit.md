# Source audit · September 9, 2026

The live Kaggle data tab lists two documentation files (`README.md`, `AGENTS.md`), totaling
40.53 kB. This project generates trajectory data through the public official simulator;
there is no train/test target table to feature-engineer.

The package is pinned to `kaggle-environments==1.32.7`. The installed Kaggriculture interpreter
matched the upstream `master` interpreter byte for byte when inspected. Future upstream updates
must trigger a new source audit; the environment's internal `0.1.0` specification version alone
is insufficient to identify mechanics. Engine file hashes are in `reports/foundation.json`.

| Finding from the executable source | Consequence for features and tests |
|---|---|
| The default 720-state run includes the initial state and 719 decisions | Test the actual terminal state; do not silently lengthen the season |
| Farm actions happen before market purchases and hiring | Buying seeds cannot enable planting in the same turn; new hands act next turn |
| The planting day starts with one missed watering count | An unwatered new plant can die at the first refresh |
| Seeds are shared among workers; excess simultaneous requests block every plant of that crop | Joint action feasibility needs a shared seed budget |
| Workers reset every day; hire cost follows 1, 1, 2, 3, 5, … | Marginal labor value depends on the remaining hours and accessible work |
| End-of-day inventories are dropped into a 100-item shed; excess is lost | Model capacity and liquidation deadlines explicitly |
| Prices change per unit of concurrent trades; floor-price sales do not add inventory | Value a batch using the price curve, not quantity times the displayed price |
| Shops are sampled with replacement and consume independently | Count duplicate shops; current demand differs from guessed future demand |
| Upcoming shops and the episode seed are hidden from agents | Compute features from callback observations, never complete episode state |
| Built-in `random` instantiates an unseeded RNG on each call | Do not call its results reproducible merely because the environment is seeded |
| The official starter is a narrow carrot loop and does not clear weeds | Use it to test the harness; it is not a strong competitive reference |
| The animal refresh applies previously banked care before banking today's care | Test this timing before implementing animal lifetime-value forecasts |

Current feature `sell_5_revenue`/`sell_20_revenue` is an exact **conditional immediate-sale
scenario with no simultaneous opponent order**. It is not a forecast. Current daily town
demand extrapolates visible shops at their current rates; it does not know future unlocks.

The feature interface excludes timing budgets, seed IDs, rewards, opponent private inventory,
future replay records, and engine internals. Episode IDs, policy labels, and seeds remain audit
metadata. A future learner must not accidentally include them as predictors.

The full legal constraints and dates should be rechecked before any actual submission.
The rules page showed that the user's account had already accepted the competition rules.
The observed final submission deadline was September 30, 2026 at 23:59 UTC. Local calls do not
certify sandbox timing, archive packaging, Kaggle validation episodes, or leaderboard receipt.
