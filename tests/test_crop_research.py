"""Mechanics parity, information boundaries and paired experimental integrity."""

import copy

import pandas as pd
import pytest
from test_foundation import initial_observation

from kaggriculture_research.crop_policy import VARIANTS, CropPolicy, crop_scenario, water_features
from kaggriculture_research.environment import game
from kaggriculture_research.experiment import paired_summary, run_game


@pytest.fixture(scope="module")
def observation():
    return initial_observation()


@pytest.mark.parametrize("crop", sorted(game.CROPS))
@pytest.mark.parametrize("remaining", [120, 719])
def test_irrigated_scenario_yield_matches_official_interpreter(crop, remaining):
    scenario = crop_scenario(crop, 10000, remaining, 0)
    if not scenario.bankable:
        assert scenario.units == 0
        return
    farm = game._new_farm(10, 3000)
    private = game._new_private()
    private["seeds"][crop] = 1
    game._apply_unit_action(farm, private, 0, ["PLANT", crop], 10, 0, 24)
    for day in range(scenario.harvest_age + 1):
        game._apply_unit_action(farm, private, 0, ["WATER"], 10, day, 24)
        if day < scenario.harvest_age:
            game._daily_refresh_plants(farm, day, 24)
    game._apply_unit_action(farm, private, 0, ["HARVEST"], 10, scenario.harvest_age, 24)
    assert private["inventories"][0].get(crop, 0) == scenario.units


def test_terminal_scenario_requires_time_for_harvest_and_delivery():
    assert crop_scenario("CARROT", 10000, 52, 0).bankable
    assert not crop_scenario("CARROT", 10000, 51, 0).bankable
    assert not crop_scenario("MELON", 10000, 24, 0).bankable


def test_new_plant_dies_without_planting_day_water():
    tile = game._new_plant("CARROT", 0, 24)
    assert water_features(tile, 0, 23)["dies_next_refresh"] == 1
    farm = game._new_farm(10, 3000)
    farm["tiles"][4][4] = tile
    game._daily_refresh_plants(farm, 0, 24)
    assert farm["tiles"][4][4] == {"kind": "WEED"}


def test_harvest_day_water_bonus_matches_actual_increment():
    farm, private = game._new_farm(10, 3000), game._new_private()
    tile = game._new_plant("MELON", 0, 24)
    tile.update(yield_units=5, fertilized_until_day=12)
    farm["tiles"][4][4] = tile
    expected = water_features(tile, 12, 1)["water_bonus_units"]
    before = tile["yield_units"]
    game._apply_unit_action(farm, private, 0, ["WATER"], 10, 12, 24)
    assert expected == tile["yield_units"] - before == 1


@pytest.mark.parametrize("variant", VARIANTS)
def test_policy_ignores_evaluator_metadata_and_preserves_observation(observation, variant):
    original = copy.deepcopy(observation)
    changed = copy.deepcopy(observation)
    changed.update(seed=999, future_shops=["PET_CAFE"], reward=1e12)
    changed["farms"][1]["private"] = {"shed": {"MELON": 100000}}
    policy = CropPolicy(variant)
    first = policy(observation)
    assert observation == original
    assert first == policy(changed)


def test_final_action_drops_and_sells_current_inventory(observation):
    obs = copy.deepcopy(observation)
    obs.update(step=718, day=29, hour=22)
    obs["private"]["inventories"][0]["MELON"] = 6
    policy = CropPolicy()
    action = policy(obs)
    assert action["farmer"] == ["DROP"]
    assert ["SELL", "MELON", 6] in action["market"]
    assert not any(order[0].startswith("BUY") for order in action["market"])
    assert policy.last_diagnostics["ineffective_farm_actions"] == 0


def test_joint_seed_reservations_never_oversubscribe(observation):
    obs = copy.deepcopy(observation)
    obs["private"]["seeds"]["MELON"] = 1
    obs["private"]["inventories"].append({})
    obs["farms"][0]["hands"] = [[4, 4]]
    action = CropPolicy()(obs)
    assert sum(a[0] == "PLANT" for a in [action["farmer"], *action["hands"]]) <= 1


def test_reproducible_full_game_with_active_opponent():
    args = (1101, 1, "full", "carrot_scheduler", {"episodeSteps": 720}, 3)
    first, second = run_game(*args), run_game(*args)
    assert first["semantic_sha256"] == second["semantic_sha256"]
    assert first["summary"]["ineffective_farm_actions"] == 0
    assert first["summary"]["plants"] > 0
    assert first["summary"]["harvests"] > 0


def test_paired_summary_keeps_both_seats_in_seed_clusters():
    rows = []
    for seed in [1101, 1102, 1103, 1104]:
        for seat in [0, 1]:
            for variant in VARIANTS:
                value = int(variant == "full") + seat
                rows.append(
                    dict(
                        seed=seed,
                        seat=seat,
                        variant=variant,
                        opponent="starter",
                        match_score=value,
                        coin_margin=value,
                        coins=value,
                        unsold_product_units=value,
                    )
                )
    result = paired_summary(pd.DataFrame(rows), 100, 3101)
    assert (result.seed_clusters == 4).all()
    assert (result.full_minus_ablated == 1).all()
    assert (result.bootstrap_low == 1).all()
