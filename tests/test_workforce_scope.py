"""A small real-engine coverage test; no season, reward or leaderboard evaluation."""

import runpy
from pathlib import Path

import pytest

PROBE = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/audit_workforce_scope.py")
)["probe"]


@pytest.fixture(scope="module")
def report():
    return PROBE()


def test_hire_four_then_twelve_is_legal_for_both_seats(report):
    assert report["engine"]["version"] == "1.32.7"
    assert report["maximum_hired_hands_demonstrated"] == 12
    assert [r["hiring_player"] for r in report["records"]] == [0, 1]
    assert all(r["hired_hands_after_transitions"] == [4, 12] for r in report["records"])


def test_hiring_cost_is_accounted_without_game_outcome(report):
    for row in report["records"]:
        assert row["total_hiring_cost"] == 376
        assert row["starting_money"] - row["remaining_money"] == 376
    assert report["complete_games_run"] == 0
    assert report["fixture_transitions"] == 4
    assert report["official_metric_effect_measured"] is False
    assert report["training_or_holdout_used"] is False


def test_current_fixed_schema_rejects_both_high_workforce_views(report):
    assert report["existing_staffing_feature_worker_slots"] == 4
    for row in report["records"]:
        for view in row["current_extractor_views"]:
            assert view["rejected"] is True
            assert "at most three hired hands" in view["reason"]
    assert report["actual_game_maximum_claimed"] is False
    assert report["feature_completion_gate"] == "open_research"
