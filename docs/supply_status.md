# Cash-constrained supply: execution and publication status

The preregistered 64-game experiment is complete. All 64 traces were independently
audited. All 75 required source, registration, trace, matrix and result artifacts
were downloaded from private S3 and verified by SHA-256, size, version, ETag and
AES256 encryption: 21,102,532 bytes in total. The machine-readable receipt is
[supply_cloud_verification.json](../reports/supply_cloud_verification.json).

## Measured evidence

- Four source-locked arms, four fresh development seeds, both seats and two
  frozen opponents; no validation or holdout data used.
- 1,308 candidates jointly screened on 11,584 legal observations: 754 varying,
  554 constant, 74 nonconstant duplicate groups and 1,866 high-correlation pairs.
- All candidates remain provisional; none is selected or rejected for a final model.
- Independent replay verified 46,016 candidate callbacks, 1,984 state restores,
  322,112 stock bounds and 321,664 sale intervals, with zero violations or action
  mismatches and exact product conservation.
- History/cash pooled match score was 0.625 versus bank's 0.375, but the gain
  occurred entirely against the mirror-policy opponent. The other opponent's
  match score did not improve.
- Cash bounds tightened melon inventory uncertainty, but all 16 cash/history
  action sequences were identical. No incremental policy benefit is demonstrated.
- The existing 151-test suite passed before final publication. Fresh CI checks
  and the new notebook's execution receipt complete the publication gate.

See [the research report](supply_research.md) for paired intervals, assumptions,
mechanisms, computational cost, source references and limitations.

## Recovery record

Execution paused at 55 completed games because a permission review rejected the
pending private upload. After renewed authorization, that checkpoint was uploaded
without replay, and only the nine missing games were played. A later rejection
of two derived-artifact uploads was resolved after read-only verification of the
bucket's ownership and privacy settings. No alternate destination or credentials
were used. All previously completed games were preserved.

The bucket belongs to the connected AWS account, blocks public access, and has
encryption and versioning enabled. SageMaker compute remains stopped; this study
used local CPU. Persistent S3/EBS storage can still incur charges.

## Current boundary

The canonical notebook extension is prepared for fresh-kernel CI execution; its
genuine outputs and execution receipt will be committed before final publication.
The earlier 17 research code cells are unchanged. Follow the
[recovery runbook](supply_recovery.md) to reproduce or inspect source-locked evidence.

The **broader feature-research gate remains closed**. Livestock/feed, fertilizer
loops, land expansion, adaptive crop mix, joint routing, calibrated opponent
beliefs and broader opponent coverage are not exhausted. No final model,
leaderboard performance, competition submission or overall completion is claimed.
