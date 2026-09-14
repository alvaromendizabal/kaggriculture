# Kaggriculture: arrival and production-headroom research

Start with [START_HERE.md](START_HERE.md). Run notebook 17, save it, then run notebook 18.
The two candidate policies are **not combined**. Both use the same pinned control.

| Round | Notebook | Representation | Evidence |
|---|---|---|---|
| 17 | 17_arrival_harvest_feature_ablation.ipynb | Stock available at worker arrival after intervening decay | 32 task descriptors, 12 state summaries, 62 tests, 10 Plotly views |
| 18 | 18_production_headroom_feature_ablation.ipynb | Next-refresh production unlocked by harvesting held crops | 32 task descriptors, 12 state summaries, 62 tests, 10 Plotly views |

Read [FEATURE_RESEARCH.md](FEATURE_RESEARCH.md) for hypotheses, assumptions, exclusions and decisions.
Read [RESULTS_REVIEW.md](RESULTS_REVIEW.md) for the actual previous result.
Read [LOCAL_VALIDATION.json](LOCAL_VALIDATION.json) for exactly what was tested here.

The shipped live notebooks are unexecuted. No new competitive performance is claimed.
Prior manual work and raw data are preserved. No remote writes, installation, AWS launch,
Git mutation, or Kaggle submission is performed by this package.
