"""Reproducible validation utilities from the September 2026 Kaggriculture sprint.

The public module contains the evaluation logic, chronology rules, and low-capacity
routing machinery used after the project discovered that its older fixed opponent
panel was badly saturated. It intentionally does not contain third-party agent
source, private replay blobs, credentials, or Kaggle submission archives.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import mean
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class EpisodeOutcome:
    episode_id: str
    score: float
    margin: float
    chronological_index: int


@dataclass(frozen=True)
class CandidateOutcome:
    episode_id: str
    score: float
    margin: float
    intervention: str | None = None


@dataclass(frozen=True)
class PromotionGate:
    minimum_net_score_units: float = 2.0
    minimum_rescues: int = 2
    maximum_sacrificed_wins: int = 1


def game_score(subject_reward: float, opponent_reward: float) -> float:
    """Return Kaggriculture win/tie/loss score for one completed game."""
    if subject_reward > opponent_reward:
        return 1.0
    if subject_reward == opponent_reward:
        return 0.5
    return 0.0


def summarize_candidate(
    keeper: Sequence[EpisodeOutcome],
    candidate: Sequence[CandidateOutcome],
) -> dict[str, float | int]:
    """Compare a candidate with the keeper on the same physical episodes."""
    keeper_by_id = {row.episode_id: row for row in keeper}
    candidate_by_id = {row.episode_id: row for row in candidate}
    if keeper_by_id.keys() != candidate_by_id.keys():
        raise ValueError("EPISODE_ALIGNMENT")

    net = 0.0
    rescues = sacrifices = ties_to_win = 0
    margins: list[float] = []
    triggers = 0
    for episode_id, base in keeper_by_id.items():
        alt = candidate_by_id[episode_id]
        net += alt.score - base.score
        margins.append(alt.margin - base.margin)
        rescues += int(base.score == 0.0 and alt.score > 0.0)
        sacrifices += int(base.score == 1.0 and alt.score < 1.0)
        ties_to_win += int(base.score == 0.5 and alt.score == 1.0)
        triggers += int(alt.intervention is not None)

    n = len(keeper_by_id)
    return {
        "episodes": n,
        "net_score_units": float(net),
        "score_gain": float(net / n) if n else 0.0,
        "rescues": rescues,
        "sacrifices": sacrifices,
        "ties_to_win": ties_to_win,
        "triggers": triggers,
        "mean_margin_gain": float(mean(margins)) if margins else 0.0,
    }


def passes_gate(metrics: Mapping[str, float | int], gate: PromotionGate) -> bool:
    return (
        float(metrics["net_score_units"]) >= gate.minimum_net_score_units
        and int(metrics["rescues"]) >= gate.minimum_rescues
        and int(metrics["sacrifices"]) <= gate.maximum_sacrificed_wins
    )


def chronological_split(
    episodes: Sequence[EpisodeOutcome], development_count: int
) -> tuple[list[EpisodeOutcome], list[EpisodeOutcome]]:
    """Create a time-ordered development/holdout split without shuffling."""
    if not 0 < development_count < len(episodes):
        raise ValueError("SPLIT_SIZE")
    ordered = sorted(episodes, key=lambda row: row.chronological_index)
    development = ordered[:development_count]
    holdout = ordered[development_count:]
    if development[-1].chronological_index >= holdout[0].chronological_index:
        raise ValueError("SPLIT_ORDER")
    return development, holdout


def validate_replay_fidelity(
    expected_rewards: Sequence[tuple[float, float]],
    reproduced_rewards: Sequence[tuple[float, float]],
) -> None:
    """Hard gate: replay-aligned validation requires exact terminal rewards."""
    if len(expected_rewards) != len(reproduced_rewards):
        raise ValueError("REPLAY_COUNT")
    for expected, reproduced in zip(expected_rewards, reproduced_rewards, strict=True):
        if tuple(map(float, expected)) != tuple(map(float, reproduced)):
            raise ValueError("REPLAY_REWARD_MISMATCH")


def rolling_origin_windows(n: int) -> list[tuple[range, range]]:
    """Registered 24-episode forward-only CV windows from the sprint."""
    if n != 24:
        raise ValueError("ROLLING_WINDOW_SIZE")
    return [
        (range(0, 12), range(12, 16)),
        (range(0, 16), range(16, 20)),
        (range(0, 20), range(20, 24)),
    ]


def rolling_cv_passes(
    fold_score_units: Sequence[float],
    total_score_units: float,
    rescues: int,
    sacrifices: int,
) -> bool:
    """Low-capacity router gate used after the first tree selector overfit."""
    return (
        len(fold_score_units) == 3
        and min(fold_score_units) >= -0.5
        and total_score_units >= 1.5
        and rescues >= 1
        and sacrifices <= 1
    )


def threshold_candidates(values: Iterable[float], max_candidates: int = 12) -> list[float]:
    values = sorted({float(v) for v in values if isfinite(float(v))})
    if len(values) < 2:
        return []
    mids = [(left + right) / 2.0 for left, right in zip(values, values[1:], strict=False)]
    if len(mids) <= max_candidates:
        return mids
    idx = sorted(
        {
            round(i * (len(mids) - 1) / (max_candidates - 1))
            for i in range(max_candidates)
        }
    )
    return [mids[i] for i in idx]


def rank_policy(metrics: Mapping[str, float | int], complexity: int = 1) -> tuple[float, ...]:
    """Win probability first; margin is only a late tie-breaker."""
    return (
        float(metrics["net_score_units"]),
        float(metrics["rescues"]),
        -float(metrics["sacrifices"]),
        float(metrics["ties_to_win"]),
        float(metrics["mean_margin_gain"]),
        -float(metrics["triggers"]),
        -float(complexity),
    )
