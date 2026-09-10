"""Tests target leakage, actual mechanics, reproducibility, and artifact integrity."""

import copy
import gzip
import json
from pathlib import Path

import pytest

from kaggriculture_research.artifacts import load_checkpoint, save_checkpoint
from kaggriculture_research.environment import (
    game,
    make_environment,
    read_protocol,
    validate_protocol,
)
from kaggriculture_research.features import observe_features, sale_revenue
from kaggriculture_research.gates import require_feature_completion
from kaggriculture_research.rollouts import run_episode, semantic_episode_hash

ROOT = Path(__file__).resolve().parents[1]


def initial_observation():
    env = make_environment(42)
    # An actual callable receives shared fields through the official environment runner.
    seen = []

    def capture(obs, config):
        seen.append(copy.deepcopy(obs))
        return game.pass_agent(obs)

    env.run([capture, "pass"])
    return seen[0]


@pytest.fixture(scope="module")
def obs():
    return initial_observation()


def test_observation_ignores_seed_reward_and_future_metadata(obs):
    altered = copy.deepcopy(obs)
    altered.update({"seed": 92834, "reward": 1e20, "future_shops": ["PET_CAFE"]})
    assert observe_features(obs).values == observe_features(altered).values


def test_opponent_private_state_is_not_a_feature_input(obs):
    altered = copy.deepcopy(obs)
    altered["farms"][1]["private"] = {"shed": {"MELON": 999999}}
    assert observe_features(obs).values == observe_features(altered).values


def test_schema_stable_under_player_swap(obs):
    changed = copy.deepcopy(obs)
    changed["player"] = 1
    assert observe_features(obs).families == observe_features(changed).families


def test_current_demand_counts_duplicate_shops(obs):
    changed = copy.deepcopy(obs)
    changed["town"]["unlocked_shops"] = ["PET_CAFE", "PET_CAFE"]
    assert observe_features(changed).values["demand.CARROT.current_daily_units"] == 25


def test_feature_extraction_does_not_mutate_observation(obs):
    before = copy.deepcopy(obs)
    observe_features(obs)
    assert obs == before


def test_price_mismatch_fails_closed(obs):
    changed = copy.deepcopy(obs)
    changed["market"]["prices"]["MELON"] = 9999
    with pytest.raises(ValueError, match="price curves"):
        observe_features(changed)


def test_unofficial_board_fails_closed(obs):
    changed = copy.deepcopy(obs)
    changed["farms"][0]["tiles"].pop()
    with pytest.raises(ValueError, match="10x10"):
        observe_features(changed)


@pytest.mark.parametrize("item", game.PRODUCTS)
def test_sale_scenario_matches_official_transaction_commits(item):
    farm = {"money": 3000.0}
    private = {"shed": {item: 20}}
    market = game._new_market()
    expected = sale_revenue(item, market["inventory"][item], 20)
    for _ in range(20):
        price = game.market_price(item, market["inventory"][item])
        assert game._commit_unit("SELL", item, price, farm, private, market)
    assert farm["money"] - 3000 == expected


def test_market_floor_does_not_accumulate_inventory():
    assert sale_revenue("MELON", 11000, 20) == 20


def test_negative_sale_rejected():
    with pytest.raises(ValueError, match="nonnegative"):
        sale_revenue("MELON", 10000, -1)


def test_checkpoint_resume_and_changed_lineage(tmp_path):
    path = tmp_path / "episode.json.gz"
    save_checkpoint(path, {"engine": "a"}, {"reward": 3100})
    assert load_checkpoint(path, {"engine": "a"}) == {"reward": 3100}
    assert load_checkpoint(path, {"engine": "b"}) is None


def test_checkpoint_tampering_rejected(tmp_path):
    path = tmp_path / "episode.json.gz"
    save_checkpoint(path, {}, {"reward": 3000})
    envelope = json.loads(gzip.decompress(path.read_bytes()))
    envelope["payload"]["reward"] = 99000
    path.write_bytes(gzip.compress(json.dumps(envelope).encode()))
    with pytest.raises(ValueError, match="checksum"):
        load_checkpoint(path, {})


def test_seed_partitions_are_disjoint():
    protocol = read_protocol(ROOT)
    protocol["holdout_seeds"][0] = protocol["development_seeds"][0]
    with pytest.raises(ValueError, match="overlap"):
        validate_protocol(protocol)


def test_unseeded_random_policy_not_accepted():
    protocol = read_protocol(ROOT)
    protocol["opponent_agent"] = "random"
    with pytest.raises(ValueError, match="deterministic"):
        validate_protocol(protocol)


def test_feature_completion_is_not_assumed():
    with pytest.raises(ValueError, match="gate remains closed"):
        require_feature_completion({"lineage_verified": True})


def test_repeated_official_episode_is_deterministic():
    first = run_episode(1101, 0, {"episodeSteps": 720})
    second = run_episode(1101, 0, {"episodeSteps": 720})
    assert semantic_episode_hash(first) == semantic_episode_hash(second)
    assert first["statuses"] == ["DONE", "DONE"]
    assert first["states"] == 720
    assert first["decision_steps"] == 719


def test_same_turn_seed_buy_cannot_supply_plant():
    env = make_environment(42)
    env.step(
        [
            {"farmer": ["PLANT", "CARROT"], "market": [["BUY_SEED", "CARROT", 1]]},
            game.pass_agent({}),
        ]
    )
    assert env.state[0].observation.farms[0]["tiles"][4][4] is None
    assert env.state[0].observation.private["seeds"]["CARROT"] == 1


def test_planting_day_requires_water_to_survive_refresh():
    tile = game._new_plant("CARROT", 0, 24)
    farm = {"tiles": [[tile]]}
    game._daily_refresh_plants(farm, 0, 24)
    assert farm["tiles"][0][0] == {"kind": "WEED"}
