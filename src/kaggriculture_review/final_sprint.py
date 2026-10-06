"""Reproducible validation utilities from the September 2026 Kaggriculture sprint.

The public module contains the evaluation logic, chronology rules, and low-capacity
routing machinery used after the project discovered that its older fixed opponent
panel was badly saturated. It intentionally does not contain third-party agent
source, private replay blobs, credentials, or Kaggle submission archives.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from math import isclose, isfinite
from statistics import mean


def _finite(value: float, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field}: expected a finite number")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(f"{field}: expected a finite number") from exc
    if not isfinite(number):
        raise ValueError(f"{field}: expected a finite number")
    return number


def _count(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field}: expected a nonnegative integer")
    return value


def _outcome(episode_id: str, score: float, margin: float) -> None:
    if not isinstance(episode_id, str) or not episode_id.strip():
        raise ValueError("EPISODE_ID")
    if _finite(score, "SCORE") not in (0.0, 0.5, 1.0):
        raise ValueError("SCORE: expected win/tie/loss score")
    _finite(margin, "MARGIN")


def _unique_episodes(rows: Sequence[EpisodeOutcome | CandidateOutcome]) -> None:
    if not rows:
        raise ValueError("EMPTY_EPISODES")
    if len({row.episode_id for row in rows}) != len(rows):
        raise ValueError("DUPLICATE_EPISODE_ID")


@dataclass(frozen=True)
class EpisodeOutcome:
    episode_id: str
    score: float
    margin: float
    chronological_index: int

    def __post_init__(self) -> None:
        _outcome(self.episode_id, self.score, self.margin)
        _count(self.chronological_index, "CHRONOLOGICAL_INDEX")


@dataclass(frozen=True)
class CandidateOutcome:
    episode_id: str
    score: float
    margin: float
    intervention: str | None = None

    def __post_init__(self) -> None:
        _outcome(self.episode_id, self.score, self.margin)
        if self.intervention is not None and (
            not isinstance(self.intervention, str) or not self.intervention.strip()
        ):
            raise ValueError("INTERVENTION")


@dataclass(frozen=True)
class PromotionGate:
    minimum_net_score_units: float = 2.0
    minimum_rescues: int = 2
    maximum_sacrificed_wins: int = 1

    def __post_init__(self) -> None:
        if _finite(self.minimum_net_score_units, "MINIMUM_NET_SCORE_UNITS") < 0:
            raise ValueError("MINIMUM_NET_SCORE_UNITS")
        _count(self.minimum_rescues, "MINIMUM_RESCUES")
        _count(self.maximum_sacrificed_wins, "MAXIMUM_SACRIFICED_WINS")


def game_score(subject_reward: float, opponent_reward: float) -> float:
    """Return Kaggriculture win/tie/loss score for one completed game."""
    subject_reward = _finite(subject_reward, "SUBJECT_REWARD")
    opponent_reward = _finite(opponent_reward, "OPPONENT_REWARD")
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
    _unique_episodes(keeper)
    _unique_episodes(candidate)
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
    net = _finite(metrics["net_score_units"], "NET_SCORE_UNITS")
    rescues = _count(metrics["rescues"], "RESCUES")
    sacrifices = _count(metrics["sacrifices"], "SACRIFICES")
    return (
        net >= gate.minimum_net_score_units
        and rescues >= gate.minimum_rescues
        and sacrifices <= gate.maximum_sacrificed_wins
    )


def chronological_split(
    episodes: Sequence[EpisodeOutcome], development_count: int
) -> tuple[list[EpisodeOutcome], list[EpisodeOutcome]]:
    """Create a time-ordered development/holdout split without shuffling."""
    _unique_episodes(episodes)
    _count(development_count, "DEVELOPMENT_COUNT")
    if not 0 < development_count < len(episodes):
        raise ValueError("SPLIT_SIZE")
    if len({row.chronological_index for row in episodes}) != len(episodes):
        raise ValueError("DUPLICATE_CHRONOLOGICAL_INDEX")
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
    if not expected_rewards or len(expected_rewards) != len(reproduced_rewards):
        raise ValueError("REPLAY_COUNT")
    for expected, reproduced in zip(expected_rewards, reproduced_rewards, strict=True):
        if len(expected) != 2 or len(reproduced) != 2:
            raise ValueError("REPLAY_REWARD_PAIR")
        expected_pair = tuple(_finite(value, "REPLAY_REWARD") for value in expected)
        reproduced_pair = tuple(_finite(value, "REPLAY_REWARD") for value in reproduced)
        if expected_pair != reproduced_pair:
            raise ValueError("REPLAY_REWARD_MISMATCH")


def rolling_origin_windows(n: int) -> list[tuple[range, range]]:
    """Registered 24-episode forward-only CV windows from the sprint."""
    if _count(n, "ROLLING_WINDOW_SIZE") != 24:
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
    folds = [_finite(value, "FOLD_SCORE_UNITS") for value in fold_score_units]
    total = _finite(total_score_units, "TOTAL_SCORE_UNITS")
    _count(rescues, "RESCUES")
    _count(sacrifices, "SACRIFICES")
    if not isclose(sum(folds), total, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("ROLLING_TOTAL_MISMATCH")
    return (
        len(fold_score_units) == 3
        and min(folds) >= -0.5
        and total >= 1.5
        and rescues >= 1
        and sacrifices <= 1
    )


def threshold_candidates(values: Iterable[float], max_candidates: int = 12) -> list[float]:
    """Return bounded finite midpoints; reject malformed training features."""
    if _count(max_candidates, "MAX_CANDIDATES") == 0:
        raise ValueError("MAX_CANDIDATES")
    values = sorted({_finite(v, "THRESHOLD_VALUE") for v in values})
    if len(values) < 2:
        return []
    mids = [left / 2.0 + right / 2.0 for left, right in zip(values, values[1:], strict=False)]
    if len(mids) <= max_candidates:
        return mids
    if max_candidates == 1:
        return [mids[(len(mids) - 1) // 2]]
    idx = sorted({round(i * (len(mids) - 1) / (max_candidates - 1)) for i in range(max_candidates)})
    return [mids[i] for i in idx]


def rank_policy(metrics: Mapping[str, float | int], complexity: int = 1) -> tuple[float, ...]:
    """Win probability first; margin is only a late tie-breaker."""
    _count(complexity, "COMPLEXITY")
    for field in ("rescues", "sacrifices", "ties_to_win", "triggers"):
        _count(metrics[field], field.upper())
    _finite(metrics["net_score_units"], "NET_SCORE_UNITS")
    _finite(metrics["mean_margin_gain"], "MEAN_MARGIN_GAIN")
    return (
        float(metrics["net_score_units"]),
        float(metrics["rescues"]),
        -float(metrics["sacrifices"]),
        float(metrics["ties_to_win"]),
        float(metrics["mean_margin_gain"]),
        -float(metrics["triggers"]),
        -float(complexity),
    )
