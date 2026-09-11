"""Mechanics and attribution tests for staffing-controlled routing research."""

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from kaggriculture_research.environment import game, make_environment
from kaggriculture_research.features import PUBLIC_FIELDS
from kaggriculture_staffing.features import FEATURE_COUNT, staffing_features
from kaggriculture_staffing.policy import StaffingPolicy

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def initial_obs():
    env = make_environment(1601)
    captured = []

    def capture(obs, config):
        if not captured:
            captured.append({k: copy.deepcopy(obs[k]) for k in PUBLIC_FIELDS})
        return game.pass_agent(obs)

    env.run([capture, "pass"])
    return captured[0]


def terminalized(obs: dict, hour: int = 0) -> dict:
    changed = copy.deepcopy(obs)
    changed["day"] = 29
    changed["hour"] = hour
    changed["step"] = 29 * 24 + hour
    return changed


def test_protocol_is_fresh_bounded_development_only():
    protocol = json.loads((ROOT / "configs/staffing_research.json").read_text())
    foundation = json.loads((ROOT / "configs/research.json").read_text())
    used = set(
        foundation["development_seeds"]
        + foundation["validation_seeds"]
        + foundation["holdout_seeds"]
    )
    for name in ("market", "supply", "livestock", "terminal"):
        used.update(
            json.loads((ROOT / f"configs/{name}_research.json").read_text())["development_seeds"]
        )
    assert protocol["development_seeds"] == [1601, 1602]
    assert not set(protocol["development_seeds"]) & used
    assert protocol["max_games"] == 8
    assert protocol["max_new_games_per_batch"] == 1
    assert protocol["holdout_allowed"] is False
    assert protocol["validation_allowed"] is False
    assert protocol["scale_up_automatic"] is False


def test_staffing_feature_schema_is_fixed_finite_and_observation_only(initial_obs):
    before = copy.deepcopy(initial_obs)
    vector = staffing_features(initial_obs)
    assert len(vector.values) == FEATURE_COUNT == 53
    assert all(np.isfinite(list(vector.values.values())))
    assert vector.values["staffing.final_day"] == 0
    assert initial_obs == before

    altered = copy.deepcopy(initial_obs)
    altered.update({"reward": 9e99, "seed": 999999, "future_shops": ["PET_CAFE"]})
    assert staffing_features(altered).values == vector.values


def test_terminal_features_activate_without_schema_drift(initial_obs):
    vector = staffing_features(terminalized(initial_obs))
    assert len(vector.values) == FEATURE_COUNT
    assert vector.values["staffing.final_day"] == 1
    assert vector.values["staffing.active_units"] == 1
    assert vector.values["staffing.hiring_window_open"] == 1
    assert vector.values["staffing.routes_retained"] >= 0


def test_arms_are_identical_before_terminal_intervention(initial_obs):
    sequential = StaffingPolicy("sequential")
    coordinated = StaffingPolicy("coordinated")
    first = sequential(copy.deepcopy(initial_obs))
    second = coordinated(copy.deepcopy(initial_obs))
    assert first == second
    assert (
        sequential.last_diagnostics["market_orders"]
        == coordinated.last_diagnostics["market_orders"]
    )


def test_terminal_market_and_hiring_rule_is_shared(initial_obs):
    obs = terminalized(initial_obs)
    sequential = StaffingPolicy("sequential")
    coordinated = StaffingPolicy("coordinated")
    sequential_action = sequential(copy.deepcopy(obs))
    coordinated_action = coordinated(copy.deepcopy(obs))
    assert sequential_action["market"] == coordinated_action["market"]
    assert sequential.last_diagnostics["hire_orders"] == coordinated.last_diagnostics["hire_orders"]
    assert (
        sequential.last_diagnostics["active_workers"]
        == coordinated.last_diagnostics["active_workers"]
    )
    assert len(coordinated_action["hands"]) == len(obs["farms"][obs["player"]]["hands"])


def test_policy_state_roundtrip_preserves_arm(initial_obs):
    policy = StaffingPolicy("coordinated")
    policy(copy.deepcopy(initial_obs))
    restored = StaffingPolicy.from_state_dict(policy.state_dict())
    assert restored.arm == "coordinated"
    assert restored.state_dict() == policy.state_dict()


def test_invalid_arm_fails_closed():
    with pytest.raises(ValueError, match="Unknown staffing arm"):
        StaffingPolicy("magic")
