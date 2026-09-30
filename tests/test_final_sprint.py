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
