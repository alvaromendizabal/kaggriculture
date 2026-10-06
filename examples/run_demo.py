"""Run a fictional paired-evaluation example without games, data, or cloud services."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaggriculture_review.final_sprint import (  # noqa: E402
    CandidateOutcome,
    EpisodeOutcome,
    PromotionGate,
    chronological_split,
    passes_gate,
    summarize_candidate,
)

# Authored fictional outcomes, not sampled from private or competition episodes.
# The last two episodes are reserved: no candidate outcomes are defined for them.
TOY_KEEPER = (
    EpisodeOutcome("toy-01", 1.0, 10.0, 1),
    EpisodeOutcome("toy-02", 1.0, 8.0, 2),
    EpisodeOutcome("toy-03", 1.0, 4.0, 3),
    EpisodeOutcome("toy-04", 0.0, -7.0, 4),
    EpisodeOutcome("toy-05", 0.0, -6.0, 5),
    EpisodeOutcome("toy-06", 0.0, -3.0, 6),
    EpisodeOutcome("toy-07", 0.5, 0.0, 7),
    EpisodeOutcome("toy-08", 1.0, 5.0, 8),
)
TOY_CANDIDATE = (
    CandidateOutcome("toy-01", 0.0, -1.0, "toy-change"),
    CandidateOutcome("toy-02", 0.0, -1.0, "toy-change"),
    CandidateOutcome("toy-03", 1.0, 4.0),
    CandidateOutcome("toy-04", 1.0, 2.0, "toy-change"),
    CandidateOutcome("toy-05", 1.0, 2.0, "toy-change"),
    CandidateOutcome("toy-06", 1.0, 2.0, "toy-change"),
)


def _require(condition: bool, message: str) -> None:
    """Keep example acceptance checks active even under python -O."""
    if not condition:
        raise ValueError(message)


def _rejection(operation: Callable[[], object], expected: str) -> str:
    try:
        operation()
    except ValueError as exc:
        _require(str(exc) == expected, f"UNEXPECTED_REJECTION: {exc}")
        return expected
    raise ValueError(f"MISSING_EXPECTED_REJECTION: {expected}")


def run_demo() -> dict[str, object]:
    """Demonstrate tradeoffs, untouched holdout IDs, and invalid pairing guards."""
    # Reverse input deliberately: chronological_split must restore time order.
    development, holdout = chronological_split(TOY_KEEPER[::-1], development_count=6)
    development_ids = [row.episode_id for row in development]
    holdout_ids = [row.episode_id for row in holdout]
    _require(not set(development_ids) & set(holdout_ids), "TOY_SPLIT_OVERLAP")
    _require(
        max(row.chronological_index for row in development)
        < min(row.chronological_index for row in holdout),
        "TOY_TIME_ORDER",
    )
    _require(
        {row.episode_id for row in TOY_CANDIDATE} == set(development_ids),
        "TOY_CANDIDATE_USES_HOLDOUT",
    )

    # These explicit thresholds are only for this fictional teaching example.
    gate = PromotionGate(
        minimum_net_score_units=1.0,
        minimum_rescues=2,
        maximum_sacrificed_wins=1,
    )
    metrics = summarize_candidate(development, TOY_CANDIDATE)
    keeper_rate = mean(row.score for row in development)
    candidate_rate = mean(row.score for row in TOY_CANDIDATE)
    accepted = passes_gate(metrics, gate)
    _require(candidate_rate > keeper_rate, "TOY_MEAN_DID_NOT_IMPROVE")
    _require(metrics["net_score_units"] >= gate.minimum_net_score_units, "TOY_GAIN_GATE")
    _require(metrics["rescues"] >= gate.minimum_rescues, "TOY_RESCUE_GATE")
    _require(metrics["sacrifices"] > gate.maximum_sacrificed_wins, "TOY_SACRIFICE_GATE")
    _require(not accepted, "TOY_UNSAFE_PROMOTION")

    guards = {
        "duplicate_keeper": _rejection(
            lambda: summarize_candidate([*development, development[0]], TOY_CANDIDATE),
            "DUPLICATE_EPISODE_ID",
        ),
        "duplicate_candidate": _rejection(
            lambda: summarize_candidate(development, [*TOY_CANDIDATE, TOY_CANDIDATE[0]]),
            "DUPLICATE_EPISODE_ID",
        ),
        "misaligned_candidate": _rejection(
            lambda: summarize_candidate(development, TOY_CANDIDATE[:-1]),
            "EPISODE_ALIGNMENT",
        ),
    }
    return {
        "scope": "Authored synthetic outcomes; not official games or leaderboard evidence.",
        "development": {
            "keeper_score_rate": keeper_rate,
            "candidate_score_rate": candidate_rate,
            "metrics": metrics,
            "toy_gate": asdict(gate),
            "decision": "REJECTED_SACRIFICED_WINS",
            "accepted": accepted,
        },
        "chronology": {
            "development_ids": development_ids,
            "reserved_holdout_ids": holdout_ids,
            "candidate_evaluated_on_holdout": False,
        },
        "rejected_invalid_inputs": guards,
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2, sort_keys=True, allow_nan=False))
