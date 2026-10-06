import math

import pytest

from kaggriculture_research.final_sprint import (
    CandidateOutcome,
    EpisodeOutcome,
    PromotionGate,
    chronological_split,
    game_score,
    passes_gate,
    rank_policy,
    rolling_cv_passes,
    rolling_origin_windows,
    summarize_candidate,
    threshold_candidates,
    validate_replay_fidelity,
)


def test_game_score():
    assert game_score(2, 1) == 1.0
    assert game_score(1, 1) == 0.5
    assert game_score(0, 1) == 0.0


def test_ladder_summary_counts_rescues_and_sacrifices():
    keeper = [
        EpisodeOutcome("a", 0.0, -10, 0),
        EpisodeOutcome("b", 1.0, 10, 1),
        EpisodeOutcome("c", 0.5, 0, 2),
    ]
    candidate = [
        CandidateOutcome("a", 1.0, 4, "route"),
        CandidateOutcome("b", 0.5, 1, "route"),
        CandidateOutcome("c", 1.0, 2, None),
    ]
    metrics = summarize_candidate(keeper, candidate)
    assert metrics["net_score_units"] == 1.0
    assert metrics["rescues"] == 1
    assert metrics["sacrifices"] == 1
    assert metrics["ties_to_win"] == 1
    assert metrics["triggers"] == 2


def test_registered_promotion_gate():
    gate = PromotionGate()
    good = {"net_score_units": 2.0, "rescues": 2, "sacrifices": 1}
    bad = {"net_score_units": 1.5, "rescues": 3, "sacrifices": 0}
    assert passes_gate(good, gate)
    assert not passes_gate(bad, gate)


def test_chronological_split_never_shuffles():
    rows = [EpisodeOutcome(str(i), 0.0, 0.0, i) for i in reversed(range(6))]
    dev, holdout = chronological_split(rows, 3)
    assert [row.chronological_index for row in dev] == [0, 1, 2]
    assert [row.chronological_index for row in holdout] == [3, 4, 5]


def test_exact_replay_fidelity_is_hard_gate():
    validate_replay_fidelity([(1, 2), (3, 4)], [(1, 2), (3, 4)])
    try:
        validate_replay_fidelity([(1, 2)], [(1, 3)])
    except ValueError as exc:
        assert str(exc) == "REPLAY_REWARD_MISMATCH"
    else:
        raise AssertionError("mismatch must fail")


def test_rolling_windows_are_forward_only():
    folds = rolling_origin_windows(24)
    assert [(max(train), min(val)) for train, val in folds] == [(11, 12), (15, 16), (19, 20)]


def test_rolling_gate_and_policy_rank():
    assert rolling_cv_passes([0.5, 0.5, 0.5], 1.5, rescues=1, sacrifices=1)
    assert not rolling_cv_passes([0.5, -1.0, 2.0], 1.5, rescues=2, sacrifices=0)
    a = {
        "net_score_units": 2,
        "rescues": 2,
        "sacrifices": 0,
        "ties_to_win": 0,
        "mean_margin_gain": 0,
        "triggers": 2,
    }
    b = {
        "net_score_units": 2,
        "rescues": 1,
        "sacrifices": 0,
        "ties_to_win": 1,
        "mean_margin_gain": 9999,
        "triggers": 1,
    }
    assert rank_policy(a) > rank_policy(b)


def test_threshold_candidates_are_bounded():
    out = threshold_candidates(range(100), max_candidates=12)
    assert len(out) <= 12
    assert out == sorted(out)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "1"])
def test_rewards_reject_nonfinite_or_coerced_values(value):
    with pytest.raises(ValueError):
        game_score(value, 0)
    with pytest.raises(ValueError):
        validate_replay_fidelity([(value, 0)], [(value, 0)])


@pytest.mark.parametrize("score", [0.2, -1, 2, math.nan, True])
def test_outcomes_require_discrete_scores(score):
    with pytest.raises(ValueError):
        EpisodeOutcome("a", score, 0, 0)
    with pytest.raises(ValueError):
        CandidateOutcome("a", score, 0)


@pytest.mark.parametrize("index", [-1, 1.5, True, math.inf])
def test_chronology_requires_nonnegative_integer(index):
    with pytest.raises(ValueError):
        EpisodeOutcome("a", 1, 0, index)


def test_summary_rejects_duplicate_or_missing_episodes():
    keeper = [EpisodeOutcome("a", 0, 0, 0)]
    candidate = [CandidateOutcome("a", 1, 0)]
    with pytest.raises(ValueError, match="DUPLICATE_EPISODE_ID"):
        summarize_candidate(keeper * 2, candidate)
    with pytest.raises(ValueError, match="DUPLICATE_EPISODE_ID"):
        summarize_candidate(keeper, candidate * 2)
    with pytest.raises(ValueError, match="EMPTY_EPISODES"):
        summarize_candidate([], [])
    with pytest.raises(ValueError, match="EPISODE_ALIGNMENT"):
        summarize_candidate(keeper, [CandidateOutcome("b", 1, 0)])


def test_split_rejects_duplicate_time_even_inside_development():
    rows = [EpisodeOutcome(str(i), 0, 0, j) for i, j in enumerate([0, 0, 1, 2])]
    with pytest.raises(ValueError, match="DUPLICATE_CHRONOLOGICAL_INDEX"):
        chronological_split(rows, 3)


def test_replay_fidelity_rejects_empty_or_malformed_pairs():
    with pytest.raises(ValueError, match="REPLAY_COUNT"):
        validate_replay_fidelity([], [])
    with pytest.raises(ValueError, match="REPLAY_REWARD_PAIR"):
        validate_replay_fidelity([(1,)], [(1,)])


def test_promotion_cannot_truncate_fractional_counts():
    with pytest.raises(ValueError, match="RESCUES"):
        passes_gate({"net_score_units": 3, "rescues": 2.9, "sacrifices": 0}, PromotionGate())
    with pytest.raises(ValueError, match="MINIMUM_NET_SCORE_UNITS"):
        PromotionGate(minimum_net_score_units=math.nan)


def test_rolling_gate_requires_consistent_aggregate():
    with pytest.raises(ValueError, match="ROLLING_TOTAL_MISMATCH"):
        rolling_cv_passes([0, 0, 0], 2, 1, 0)
    with pytest.raises(ValueError, match="SACRIFICES"):
        rolling_cv_passes([0.5, 0.5, 0.5], 1.5, 1, -1)


def test_single_threshold_and_extreme_finite_values():
    assert len(threshold_candidates(range(10), max_candidates=1)) == 1
    assert threshold_candidates([1e308, 1.7e308]) == [1.35e308]
    assert threshold_candidates([1]) == []
    with pytest.raises(ValueError, match="MAX_CANDIDATES"):
        threshold_candidates(range(10), max_candidates=0)
    with pytest.raises(ValueError, match="THRESHOLD_VALUE"):
        threshold_candidates([0, math.nan, 1])


def test_policy_rank_rejects_nan_margin():
    metrics = {
        "net_score_units": 2,
        "rescues": 2,
        "sacrifices": 0,
        "ties_to_win": 0,
        "mean_margin_gain": math.nan,
        "triggers": 2,
    }
    with pytest.raises(ValueError, match="MEAN_MARGIN_GAIN"):
        rank_policy(metrics)
