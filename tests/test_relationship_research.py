"""Independent interpreter parity and causal information/interaction contracts."""

import copy
import json
from itertools import product
from pathlib import Path

import pandas as pd
import pytest
from test_foundation import initial_observation

from kaggriculture_research.artifacts import load_checkpoint, save_checkpoint
from kaggriculture_research.crop_policy import CropPolicy
from kaggriculture_research.environment import game
from kaggriculture_research.progress import Progress
from kaggriculture_research.relationship_experiment import episode_hash, factorial_summary, run_game
from kaggriculture_research.relationship_features import (
    CausalHistory,
    animal_refresh,
    capped_ready,
    cash_reserve,
    inventory_pressure,
    plant_refresh,
    relationship_features,
    town_consumption,
)
from kaggriculture_research.relationship_policy import ARMS, RelationshipPolicy


@pytest.fixture(scope="module")
def observation():
    return initial_observation()


@pytest.mark.parametrize("crop", sorted(game.CROPS))
def test_plant_treatment_refresh_parity_at_all_ages_and_caps(crop):
    for age, water, fertilize, drought, units in product(
        range(18), (False, True), (False, True), (0, 1), (0, 1, 4, 6)
    ):
        p = game.CROPS[crop]
        if units > p["max_yield"]:
            continue
        tile = game._new_plant(crop, 0, 24)
        tile.update(yield_units=units, consecutive_unwatered=drought)
        expected = plant_refresh(tile, age, water, fertilize)
        farm, private = game._new_farm(10, 3000), game._new_private()
        farm["tiles"][4][4] = copy.deepcopy(tile)
        private["inventories"][0]["FERTILIZER"] = 1
        if fertilize:
            game._apply_unit_action(farm, private, 0, ["FERTILIZE"], 10, age, 24)
        if water:
            game._apply_unit_action(farm, private, 0, ["WATER"], 10, age, 24)
        game._daily_refresh_plants(farm, age, 24)
        result = farm["tiles"][4][4]
        assert expected["dead"] == (result["kind"] == "WEED")
        assert expected["units"] == result.get("yield_units", 0)


@pytest.mark.parametrize("animal", sorted(game.ANIMALS))
def test_animal_feed_care_refresh_parity_at_production_and_cap(animal):
    for age, feed, care, drought, bank, units in product(
        range(12),
        (False, True),
        (False, True),
        (0, 1),
        (0, 2),
        (0, game.ANIMALS[animal]["max_held"]),
    ):
        tile = game._new_animal(animal, 0)
        tile.update(yield_units=units, consecutive_unfed=drought, pending_care_bonus=bank)
        expected = animal_refresh(tile, age, feed, care)
        farm, private = game._new_farm(10, 3000), game._new_private()
        farm["tiles"][4][4] = copy.deepcopy(tile)
        private["inventories"][0]["WHEAT"] = 1
        if feed:
            game._apply_unit_action(farm, private, 0, ["FEED"], 10, age, 24)
        if care:
            game._apply_unit_action(farm, private, 0, ["CARE"], 10, age, 24)
        game._daily_refresh_animals(farm, age)
        result = farm["tiles"][4][4]
        assert expected["escaped"] == ("animal" not in result)
        assert expected["units"] == result.get("yield_units", 0)
        assert expected["bank"] == result.get("pending_care_bonus", 0)


def test_town_event_alignment_includes_current_action_and_duplicate_shops():
    shops = ["PET_CAFE", "PET_CAFE", "BAKERY"]
    for step, horizon, item in product(range(25), (0, 1, 4, 24, 72), game.PRODUCTS):
        expected = sum(
            (
                sum(2 if len(game.SHOPS[s]) == 1 else 1 for s in shops if item in game.SHOPS[s])
                if t % 4 == 0
                else 0
            )
            + int(t % 24 == 0 and item in game.TOWN_CENTER_PRODUCTS)
            for t in range(step, step + horizon)
        )
        assert town_consumption(shops, item, step, horizon) == expected
    assert town_consumption(shops, "CARROT", 24, 1) == 5


def test_drop_and_market_phases_have_different_capacity(observation):
    obs = copy.deepcopy(observation)
    obs["private"]["shed"] = {"MELON": 90}
    obs["private"]["inventories"][0] = {"CARROT": 20}
    pressure = inventory_pressure(obs)
    assert pressure["night_overflow_if_pass"] == 10
    assert pressure["night_overflow_after_sell_all"] == 0
    action = RelationshipPolicy("100")(obs)
    assert action["farmer"] == ["PLACE", "CARROT", 10]
    assert ["SELL", "CARROT", 10] in action["market"]
    assert ["SELL", "MELON", 90] in action["market"]


def test_capacity_pressure_routes_carried_harvest_before_night(observation):
    obs = copy.deepcopy(observation)
    obs.update(step=250, day=10, hour=10)
    obs["private"]["inventories"][0] = {"MELON": 96}
    obs["farms"][0]["farmer"] = [3, 4]
    tile = game._new_plant("MELON", 0, 24)
    tile.update(yield_units=6, watered_today=True)
    obs["farms"][0]["tiles"][4][3] = tile
    assert RelationshipPolicy("100")(obs)["farmer"] == ["EAST"]


def test_capped_melon_is_ready_at_age_ten_not_twelve(observation):
    obs = copy.deepcopy(observation)
    obs.update(step=241, day=10, hour=1)
    tile = game._new_plant("MELON", 0, 24)
    tile.update(yield_units=6, watered_today=True)
    obs["farms"][0]["tiles"][4][4] = tile
    assert capped_ready(tile, 10)
    assert RelationshipPolicy("001")(obs)["farmer"] == ["HARVEST"]
    assert CropPolicy()(obs)["farmer"] != ["HARVEST"]


@pytest.mark.parametrize("arm", ARMS)
def test_no_hidden_information_or_input_mutation(observation, arm):
    obs = copy.deepcopy(observation)
    changed = copy.deepcopy(obs)
    changed.update(seed=999999, future_shops=["YARN_STORE"], reward=1e30)
    changed["farms"][1]["private"] = {"shed": {"MELON": 100000}}
    policy = RelationshipPolicy(arm)
    assert policy(obs) == policy(changed)
    assert obs == observation
    assert relationship_features(obs).values == relationship_features(changed).values


def test_history_masks_prefix_and_never_uses_future(observation):
    first, second = CausalHistory(), CausalHistory()
    for step in range(25):
        obs = copy.deepcopy(observation)
        obs["step"] = step
        obs["market"]["inventory"]["MELON"] += step
        left = first.observe(obs)
        obs.update(future_shops=["YARN_STORE"], reward=step * 100000)
        right = second.observe(obs)
        assert left.values == right.values
        assert left.values["history.lag24.available"] == int(step >= 24)
    assert left.values["history.lag24.MELON.inventory_change"] == 24
    with pytest.raises(ValueError, match="consecutive"):
        first.observe(obs)
    assert CausalHistory().observe(observation).values["history.lag1.available"] == 0


def test_feature_schema_stable_in_animal_crop_and_worker_states(observation):
    obs = copy.deepcopy(observation)
    schema = relationship_features(obs).families
    farm = obs["farms"][0]
    for i, animal in enumerate(game.ANIMALS):
        farm["tiles"][0][i] = game._new_animal(animal, 0)
    for i, crop in enumerate(game.CROPS):
        farm["tiles"][1][i] = game._new_plant(crop, 0, 24)
    for _ in range(3):
        game._do_hire(farm, obs["private"], 10)
    assert relationship_features(obs).families == schema
    obs["player"] = 1
    obs["private"] = game._new_private()
    assert relationship_features(obs).families == schema


def test_capital_reserve_is_conditional_and_does_not_spend_future_sales(observation):
    obs = copy.deepcopy(observation)
    obs["farms"][0]["money"] = 80
    obs["private"]["shed"] = {"MELON": 99}
    reserve = cash_reserve(obs)
    assert 0 < reserve["seed_spendable_cash"] < 80
    orders = RelationshipPolicy("010")(obs)["market"]
    assert not any(o[:2] == ["BUY_SEED", "MELON"] for o in orders)


def test_all_off_is_exact_frozen_policy_action(observation):
    assert RelationshipPolicy("000")(observation) == CropPolicy()(observation)


def test_factorial_effect_scaling_and_seed_clusters():
    rows = []
    for seed, seat, arm in product((1101, 1102, 1103, 1104), (0, 1), ARMS):
        a, b, c = map(int, arm)
        outcome = 3 * a + 5 * b + 7 * c + 2 * a * b + seed + seat
        rows.append(
            {
                "seed": seed,
                "seat": seat,
                "arm": arm,
                "capacity": a,
                "capital": b,
                "maturity": c,
                **{
                    m: outcome
                    for m in (
                        "match_score",
                        "coins",
                        "coin_margin",
                        "discarded_units",
                        "minimum_observed_cash",
                    )
                },
            }
        )
    effects = factorial_summary(pd.DataFrame(rows), 100, 3102)
    coins = effects[effects.metric == "coins"].set_index("contrast")
    assert coins.loc["capacity", "effect"] == 4
    assert coins.loc["capital", "effect"] == 6
    assert coins.loc["maturity", "effect"] == 7
    assert coins.loc["capacity:capital", "effect"] == 2
    assert coins.loc["capacity:capital:maturity", "effect"] == 0
    assert (effects.seed_clusters == 4).all()
    with pytest.raises(ValueError, match="Incomplete"):
        factorial_summary(pd.DataFrame(rows[:-1]), 10, 3102)


def test_full_episode_reproducibility_and_checkpoint_column_order(tmp_path):
    first, second = run_game(1101, 1, "111"), run_game(1101, 1, "111")
    assert first["semantic_sha256"] == second["semantic_sha256"]
    path, lineage = tmp_path / "episode.json.gz", {"test": "schema_and_semantics"}
    save_checkpoint(path, lineage, first)
    restored = load_checkpoint(path, lineage)
    assert restored["feature_columns"] == first["feature_columns"]
    assert restored["feature_samples"] == first["feature_samples"]
    assert episode_hash(restored) == first["semantic_sha256"]
    assert len(first["feature_columns"]) == 618


def test_complete_batch_screening_publication_and_resume(tmp_path, monkeypatch):
    """Exercise the real batch orchestrator and profiler with cheap synthetic games.

    Full-game mechanics/determinism are covered separately; this test checks the
    initialization, nested design, checkpoints, report pipeline and restart path.
    """
    import kaggriculture_research.relationship_experiment as experiment

    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/relationship_research.json").read_text())
    foundation = json.loads((root / "configs/research.json").read_text())
    (tmp_path / "reports").mkdir()
    calls, uploaded = [], []

    def simulated(seed, seat, arm, stride):
        calls.append((seed, seat, arm))
        value = int(arm, 2)
        summary = {
            "seed": seed,
            "seat": seat,
            "arm": arm,
            "match_score": float(value > 0),
            "coins": 3000 + value,
            "coin_margin": value,
            "discarded_units": 0,
            "minimum_observed_cash": 3000,
            **{f: int(bit) for f, bit in zip(experiment.FACTORS, arm, strict=True)},
        }
        payload = {
            "summary": summary,
            "latency_ms": [1.0],
            "feature_extraction_ms": [0.1],
            "feature_schema": {"z_variable": "test", "a_duplicate": "test", "constant": "test"},
            "feature_columns": ["z_variable", "a_duplicate", "constant"],
            "feature_samples": [
                {"step": 0, "values": [value, value, 0]},
                {"step": 4, "values": [value + 1, value + 1, 0]},
            ],
        }
        payload["semantic_sha256"] = experiment.episode_hash(payload)
        return payload

    monkeypatch.setattr(experiment, "run_game", simulated)
    first = experiment.run_experiment(tmp_path, protocol, foundation, Progress(), uploaded.append)
    assert len(calls) == len(uploaded) == first["games"] == 64
    assert first["reused_games"] == 0
    assert first["screening"]["generated_features"] == 3
    assert first["screening"]["constant_features"] == ["constant"]
    assert first["screening"]["exact_duplicate_groups"] == [["z_variable", "a_duplicate"]]
    assert (tmp_path / "reports/relationship_registry.csv").exists()
    first_groups = first["groups"]

    def forbidden_rerun(*args):
        raise AssertionError("A valid cached game was rerun")

    monkeypatch.setattr(experiment, "run_game", forbidden_rerun)
    second = experiment.run_experiment(tmp_path, protocol, foundation, Progress(), uploaded.append)
    assert second["reused_games"] == 64
    assert second["groups"] == first_groups
    assert second["screening"] == first["screening"]
