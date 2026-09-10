"""Finite-horizon mechanics, independent assignment checks and causal contracts."""

import copy
from itertools import product

import pytest

from kaggriculture_livestock.policy import LivestockPolicy
from kaggriculture_research.environment import game, make_environment
from kaggriculture_research.features import sale_revenue
from kaggriculture_terminal.feed_policy import service_plan
from kaggriculture_terminal.policy import TerminalPolicy
from kaggriculture_terminal.routing import ITEMS, assign, liquidation, menus, terminal_features


@pytest.fixture
def obs():
    env = make_environment(71)
    env.reset()
    observation = copy.deepcopy(env.state[0].observation)
    observation.update(day=29, hour=0, step=696)
    return observation


@pytest.mark.parametrize("species", sorted(game.ANIMALS))
def test_feed_gate_requires_a_real_refresh(obs, species):
    tile = game._new_animal(species, 0)
    tile.update(consecutive_unfed=1, pending_care_bonus=2)
    assert not service_plan(tile, obs, (4, 4), "fertilizer")["feed"]
    obs.update(day=28, step=672)
    assert service_plan(tile, obs, (4, 4), "fertilizer")["feed"]


@pytest.mark.parametrize("steps", [1, 2, 3, 5, 23])
def test_route_actions_execute_to_the_claimed_inventory(obs, steps):
    obs["step"] = 719 - steps
    obs["hour"] = obs["step"] % 24
    farm = obs["farms"][0]
    farm["farmer"] = [4, 4]
    tile = game._new_plant("WHEAT", 25, 24)
    tile["yield_units"] = 3
    farm["tiles"][4][3] = tile
    farm["tiles"][3][4] = game._new_animal("GOOSE", 0)
    farm["tiles"][3][4].update(yield_units=2, fertilizer_available=True)
    menu, _ = menus(obs)
    for route in menu[0]:
        if not route.actions:
            continue
        simulated = copy.deepcopy(obs)
        for action in route.actions:
            game._apply_unit_action(
                simulated["farms"][0], simulated["private"], 0, list(action), 10, 29, 24, 100
            )
        actual = tuple(simulated["private"]["shed"].get(i, 0) for i in ITEMS)
        assert actual == route.quantities
        assert len(route.actions) <= steps


@pytest.mark.parametrize("room", [0, 1, 3, 100])
def test_assignment_matches_independent_cartesian_optimum(obs, room):
    farm, private = obs["farms"][0], obs["private"]
    farm["hands"] = [[3, 4]]
    private["inventories"].append({})
    private["shed"] = {"WHEAT": 100 - room}
    for x in (2, 3):
        tile = game._new_animal("GOOSE", 0)
        tile.update(yield_units=2, fertilizer_available=True)
        farm["tiles"][4][x] = tile
    menu, stats = menus(obs)
    chosen, result = assign(menu, stats["room"], obs)
    expected = 0
    for routes in product(*menu):
        resources = [r for route in routes for r in route.resources]
        quantities = [sum(r.quantities[j] for r in routes) for j in range(len(ITEMS))]
        if len(resources) != len(set(resources)) or sum(quantities) > room:
            continue
        value = sum(
            sale_revenue(i, obs["market"]["inventory"][i], q)
            for i, q in zip(ITEMS, quantities, strict=True)
        )
        expected = max(expected, value - 8 * sum(len(r.actions) for r in routes))
    assert result["joint_utility"] == expected
    assert len(chosen) == 2


def test_last_callback_deposit_is_bankable_but_remote_collection_is_not(obs):
    obs.update(step=718, hour=22)
    obs["farms"][0]["farmer"] = [4, 4]
    obs["private"]["inventories"][0] = {"MILK": 2, "WOOL": 1}
    action, diagnostics = liquidation(obs)
    assert action["farmer"] == ["DROP"]
    assert action["market"] == [["SELL", "MILK", 2], ["SELL", "WOOL", 1]]
    assert diagnostics["ineffective_farm_actions"] == 0


def test_schema_metadata_invariance_and_no_mutation(obs):
    before = copy.deepcopy(obs)
    values = terminal_features(obs)
    assert len(values.values) == 79
    assert obs == before
    obs.update(seed=991, reward=1e30, future_shops=["YARN_STORE"], opponent_private={"MILK": 999})
    assert terminal_features(obs).values == values.values
    for arm in ("baseline", "feed", "joint"):
        assert TerminalPolicy(arm)(obs) == TerminalPolicy(arm)(before)
    obs.update(day=0, hour=0, step=0)
    assert terminal_features(obs).families == values.families


@pytest.mark.parametrize("arm", ["baseline", "feed", "joint"])
def test_state_restore_preserves_terminal_actions(obs, arm):
    actor = TerminalPolicy(arm)
    actor(obs)
    restored = TerminalPolicy.from_state_dict(actor.state_dict())
    obs.update(step=697, hour=1)
    assert actor(obs) == restored(obs)
    obs.update(step=699, hour=3)
    with pytest.raises(ValueError, match="consecutive"):
        restored(obs)


def test_preterminal_actions_equal_frozen_policy(obs):
    obs.update(day=28, hour=23, step=695)
    expected = LivestockPolicy("fertilizer")(obs)
    for arm in ("baseline", "feed", "joint"):
        actor = TerminalPolicy(arm)
        assert actor(obs) == expected


def test_full_shed_never_discards_carry(obs):
    obs["private"]["shed"] = {"WHEAT": 100}
    obs["private"]["inventories"][0] = {"MILK": 6}
    action, _ = liquidation(obs)
    assert action["farmer"] == ["PASS"]
    assert action["market"] == [["SELL", "WHEAT", 100]]
