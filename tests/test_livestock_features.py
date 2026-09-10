"""Resource coupling, timing, observation safety and legal execution regressions."""

import copy
from itertools import product

import pytest

from kaggriculture_livestock.features import (
    animal_service,
    fertilizer_value,
    ingredient_route,
    livestock_features,
    next_production_day,
    purchase_cost,
    service_plan,
)
from kaggriculture_livestock.policy import LivestockPolicy
from kaggriculture_research.environment import game, make_environment


@pytest.fixture
def observation():
    env = make_environment(61)
    env.reset()
    return copy.deepcopy(env.state[0].observation)


def calendar(obs, day, hour=0):
    obs["day"], obs["hour"], obs["step"] = day, hour, day * 24 + hour


@pytest.mark.parametrize("animal", sorted(game.ANIMALS))
def test_care_conversion_matches_independent_multi_refresh_treatment(animal, observation):
    p = game.ANIMALS[animal]
    for day, bank in product((0, p["first_yield_day"] - 1, 12, 20), (0, 2, p["max_held"])):
        calendar(observation, day)
        tile = game._new_animal(animal, 0)
        tile["pending_care_bonus"] = bank
        expected = animal_service(tile, observation, (4, 4))
        end_day = next_production_day(tile, day + 2)
        totals = []
        for treated in (False, True):
            farm = {"tiles": [[copy.deepcopy(tile)]]}
            total = 0
            for d in range(day, end_day):
                t = farm["tiles"][0][0]
                t["fed_today"] = True
                t["cared_today"] = treated and d == day
                t["yield_units"] = 0  # Stated collection-before-cap scenario.
                game._daily_refresh_animals(farm, d)
                total += farm["tiles"][0][0]["yield_units"]
            totals.append(total)
        assert totals[1] - totals[0] == expected["care_bonus_with_collection"]


def test_care_on_production_eve_is_not_paid_at_that_production(observation):
    calendar(observation, 7)
    tile = game._new_animal("COW", 0)
    result = animal_service(tile, observation, (4, 4))
    assert result["next_production_actions"] == 24
    assert result["care_conversion_actions"] == 72  # Milk day 10, not day 8.


def test_unfed_production_loses_banked_care_but_has_a_base_unit(observation):
    calendar(observation, 7)
    tile = game._new_animal("COW", 0)
    tile["pending_care_bonus"] = 3
    result = animal_service(tile, observation, (4, 4))
    assert result["next_refresh_units_without_feed"] == 1
    assert result["next_refresh_units_with_feed"] == 4
    assert service_plan(tile, observation, (4, 4), "feed")["feed"]
    tile["consecutive_unfed"] = 1
    assert animal_service(tile, observation, (4, 4))["replacement_coins_at_escape_risk"] == 400


def test_care_saturation_and_terminal_conversion_are_explicit(observation):
    tile = game._new_animal("SHEEP", 0)
    tile["pending_care_bonus"] = 6
    assert animal_service(tile, observation, (4, 4))["care_bonus_with_collection"] == 0
    calendar(observation, 29)
    tile["pending_care_bonus"] = 0
    assert animal_service(tile, observation, (4, 4))["care_conversion_before_terminal"] == 0
    assert not service_plan(tile, observation, (4, 4), "care")["care"]


@pytest.mark.parametrize("item", ["WHEAT", "FERTILIZER"])
def test_purchase_curve_uses_successive_pre_decrement_quotes(item):
    inv = game.MARKET_I0
    market = game._new_market()
    farm, private = game._new_farm(10, 10000), game._new_private()
    for _ in range(7):
        quote = game.market_price(item, market["inventory"][item] - 1)
        assert game._commit_unit("BUY_PRODUCT", item, quote, farm, private, market)
    assert purchase_cost(item, inv, 7) == 10000 - farm["money"]


def test_fertilizer_values_include_sale_opportunity_and_nonretroactive_water(observation):
    calendar(observation, 8)
    tile = game._new_plant("STRAWBERRY", 0, 24)
    tile["consecutive_unwatered"] = 0
    values = fertilizer_value(observation, (4, 4), tile)
    assert values["bankable_extra_units"] == 1
    assert values["current_quote_revenue_gain"] == 114
    assert values["net_scenario_value"] == 6  # Marginal curve quote 114 - manure 100 - work 8.
    already = game._new_plant("WHEAT", 0, 24)
    calendar(observation, 4)
    already.update(watered_today=True, yield_units=4)
    assert fertilizer_value(observation, (4, 4), already)["bankable_extra_units"] == 0


def test_late_fertilizer_can_displace_life_saving_water(observation):
    calendar(observation, 8, 23)
    tile = game._new_plant("STRAWBERRY", 8, 24)
    value = fertilizer_value(observation, (4, 4), tile)
    assert value["treated_harvest_units"] == 0
    assert value["net_scenario_value"] < 0


def test_manure_is_one_slot_and_ingredient_route_requires_a_pickup(observation):
    tile = game._new_animal("GOOSE", 0)
    farm = {"tiles": [[tile]]}
    for day in range(3):
        tile["fed_today"] = True
        game._daily_refresh_animals(farm, day)
        assert tile["fertilizer_available"] is True
    assert ingredient_route(observation, (3, 4), "WHEAT") is None
    observation["private"]["shed"]["WHEAT"] = 1
    assert ingredient_route(observation, (3, 4), "WHEAT") == 2
    observation["private"]["inventories"][0]["WHEAT"] = 1
    assert ingredient_route(observation, (3, 4), "WHEAT") == 1


def test_schema_and_hidden_metadata_invariance(observation):
    empty = livestock_features(observation)
    before = copy.deepcopy(observation)
    for x, animal in enumerate(game.ANIMALS):
        observation["farms"][0]["tiles"][4][x] = game._new_animal(animal, 0)
    populated = livestock_features(observation)
    assert len(empty.values) == len(populated.values) == 234
    assert empty.families == populated.families
    clean = copy.deepcopy(observation)
    pristine = copy.deepcopy(clean)
    observation.update(
        seed=99999, reward=1e12, future_shops=["YARN_STORE"], opponent_private={"MILK": 999}
    )
    assert livestock_features(observation).values == populated.values
    first = LivestockPolicy("fertilizer")(clean)
    assert clean == pristine
    assert first == LivestockPolicy("fertilizer")(observation)
    assert clean["private"] == before["private"]


def test_state_restore_and_episode_boundary(observation):
    policy = LivestockPolicy("care")
    policy(observation)
    restored = LivestockPolicy.from_state_dict(policy.state_dict())
    observation["step"] = observation["hour"] = 1
    assert policy(observation) == restored(observation)
    observation["step"] = observation["hour"] = 3
    with pytest.raises(ValueError, match="consecutive"):
        restored(observation)


def test_registered_sources_remain_unchanged():
    import json
    from pathlib import Path

    from kaggriculture_research.artifacts import file_digest

    root = Path(__file__).resolve().parents[1]
    original = json.loads((root / "reports/supply_registration.json").read_text())
    for name, sha in original["identity"]["lineage"]["code"].items():
        assert file_digest(root / "src/kaggriculture_research" / name) == sha
