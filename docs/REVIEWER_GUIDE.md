# Reviewer guide

Start with the interactive demo, then trace the decisions to their recorded evidence.
Historical research results below refer to the September 30, 2026 evidence cutoff.

## Three-minute interactive review

Open [Farming Decision Lab](https://alvaro-farming-agent-lab.tartmacaw2.chatgpt.site) and change an input or policy to inspect the live computation. [Local launch and test instructions](REPRODUCIBILITY.md). Then follow the historical evidence path below.

1. Read the [README](../README.md) for the problem, ownership, dated results, and limitations.
2. Open the [executed portfolio notebook](../notebooks/57_portfolio_review.ipynb) for a compact
   visual review, persisted outputs, and synthetic paired-evaluation demonstration.
3. Read the [case study](../CASE_STUDY.md) for the decision to replace a saturated validator.

## Verify the important claims

| Claim | Evidence to inspect | What it does not prove |
|---|---|---|
| The fixed opponent panel overstated competitive strength | [Sprint report](../reports/final_sprint_2026-09-30.json), `validation_alignment` | That 48 dated episodes represent every future opponent |
| Native recovery was not scientifically rejected | Same report, `native_harvest_transport_failure` and `current_recovery_artifact` | A successful competitive run of the prepared recovery artifact |
| External work was tested and attributed | [Source and method matrix](research/leading_solution_reproduction_matrix.md) | Ownership of third-party controllers or their private training recipes |
| Promotion used explicit chronological gates | [Registered protocols](research/final_sprint_protocols.md) | A guarantee of live performance |
| Accepted work was reused and costs were tracked | [Outcome ledger](research/latest_outcomes.md), [manifest](../reports/final_sprint_reproduction_manifest.json) | Account-wide billing or independent authentication of unavailable raw bundles |
| Published evaluation utilities are executable | [Reproducibility guide](REPRODUCIBILITY.md), [synthetic example](../examples/README.md) | Reproduction of the private agent's rating |

## Deeper technical review

The [sprint notebook](../notebooks/56_final_sprint_ladder_alignment.ipynb) and
[sprint memo](research/final_sprint_2026-09-30.md) preserve the detailed negative experiments.
The [evaluation module](../src/kaggriculture_review/final_sprint.py) and its
[tests](../tests/test_final_sprint.py) expose the paired-comparison and chronology logic.
Review the [quality workflow](../.github/workflows/quality.yml) to distinguish lightweight
aggregate checks from the broader suite's small official-engine foundation runs.

The dated notebook/archive sequence is research history. A later correction supersedes an
earlier interpretation; historical promotion labels are not retroactively upgraded into
proof under the corrected validator.
