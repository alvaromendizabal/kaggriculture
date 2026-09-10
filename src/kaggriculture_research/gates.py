"""Fail closed: a schema audit cannot substitute for feature-family experiments."""

from typing import Any


def require_feature_completion(evidence: dict[str, Any]) -> None:
    requirements = (
        "major_families_evaluated",
        "leakage_checks_passed",
        "training_only_selection",
        "paired_family_ablations",
        "opponent_diversity",
        "seed_robustness",
        "diminishing_returns_supported",
        "lineage_verified",
    )
    missing = [name for name in requirements if evidence.get(name) is not True]
    if missing:
        raise ValueError("Feature research gate remains closed: " + ", ".join(missing))
