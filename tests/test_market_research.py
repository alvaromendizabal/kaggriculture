"""Independent market interpreter parity, information boundaries and study contracts."""

import copy
import json
from itertools import product
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from test_foundation import initial_observation

from kaggriculture_research.environment import game
from kaggriculture_research.features import observe_features
from kaggriculture_research.market_experiment import factorial_summary, run_game
from kaggriculture_research.market_features import (
    market_features,
    sale_path,
    simultaneous_sale,
    two_stage_value,
    visible_wave,
    wave_units,
)
from kaggriculture_research.market_policy import ARMS, FACTORS, MarketPolicy
from kaggriculture_research.progress import Progress
from kaggriculture_research.relationship_features import CausalHistory, relationship_features
from kaggriculture_research.relationship_policy import RelationshipPolicy


@pytest.fixture(scope="module")
def observation():
    return initial_observation()


def market_state(item, inventory, own, rival):
    market = game._new_market()
    market["inventory"][item] = inventory
    farms = [game._new_farm(10, 3000) for _ in range(2)]
    state = []
    for quantity in (own, rival):
        private = game._new_private()
        private["shed"][item] = quantity
        obs = SimpleNamespace(
            market=market,
            farms=farms,
            private=private,
            town={"unlocked_shops": ["PET_CAFE", "PET_CAFE"]},
        )
        state.append(
            SimpleNamespace(observation=obs, action={"market": [["SELL", item, quantity]]})
        )
    return state, SimpleNamespace(configuration={})


@pytest.mark.parametrize("item", game.PRODUCTS)
def test_single_and_simultaneous_sale_match_official_interpreter(item):
    p = game.MARKET_PARAMS[item]
    for offset, own, rival in product(
        (-3 * p["T"], -p["T"], -1, 0, 1, p["T"], 10 * p["T"]), (0, 1, 2, 20, 100), (0, 1, 20)
    ):
        inventory = p["I0"] + offset
        state, env = market_state(item, inventory, own, rival)
        expected = simultaneous_sale(item, inventory, own, rival)
        game._process_market(state, env)
        obs = state[0].observation
        assert expected == (
            obs.farms[0]["money"] - 3000,
            obs.farms[1]["money"] - 3000,
            obs.market["inventory"][item],
        )
        if rival == 0:
            assert sale_path(item, inventory, own) == (expected[0], expected[2])


@pytest.mark.parametrize("item", game.PRODUCTS)
def test_two_stage_paths_replay_exactly_for_the_declared_event_order(item):
    for inventory, quantity, prefix, demand, rival in product(
        (9900, 10000, 11000), (5, 20), (0, 3), (0, 12), (0, 40)
    ):
        quiet, stress = two_stage_value(item, inventory, quantity, prefix, demand, rival)
        for rival_amount, expected in ((0, quiet), (rival, stress)):
            state, env = market_state(item, inventory, quantity, rival_amount)
            state[0].action["market"] = [["SELL", item, prefix]]
            state[1].action["market"] = []
            game._process_market(state, env)
            state[0].action["market"] = []
            state[1].action["market"] = [["SELL", item, rival_amount]]
            game._process_market(state, env)
            state[0].observation.market["inventory"][item] -= demand
            state[0].action["market"] = [["SELL", item, quantity - prefix]]
            state[1].action["market"] = []
            game._process_market(state, env)
            assert state[0].observation.farms[0]["money"] - 3000 == expected


def test_visible_supply_cannot_arrive_before_harvest_and_deposit(observation):
    obs = copy.deepcopy(observation)
    obs.update(step=240, day=10, hour=0)
    tile = game._new_plant("MELON", 0, 24)
    tile.update(yield_units=6, watered_today=True)
    obs["farms"][1]["tiles"][4][4] = tile
    wave = visible_wave(obs, 1)
    assert wave_units(wave, "MELON", 0) == 0
    assert wave_units(wave, "MELON", 1) == 6
    obs["hour"] = 23
    obs["farms"][1]["farmer"] = [0, 0]
    assert wave_units(visible_wave(obs, 1), "MELON", 24) == 0
    obs["farms"][1]["farmer"] = [4, 4]
    assert wave_units(visible_wave(obs, 1), "MELON", 1) == 6


def test_feature_contract_and_terminal_masks(observation):
    obs = copy.deepcopy(observation)
    baseline = market_features(obs)
    assert len(baseline.values) == 315
    vectors = [
        observe_features(obs),
        relationship_features(obs),
        CausalHistory().observe(obs),
        baseline,
    ]
    assert len({k for v in vectors for k in v.values}) == 933
    for i, animal in enumerate(game.ANIMALS):
        tile = game._new_animal(animal, 0)
        tile["yield_units"] = 2
        obs["farms"][1]["tiles"][0][i] = tile
    for _ in range(3):
        game._do_hire(obs["farms"][0], obs["private"], 10)
    assert market_features(obs).families == baseline.families
    obs.update(step=718, day=29, hour=22)
    last = market_features(obs).values
    assert all(
        value == 0 for name, value in last.items() if any(f".h{h}." in name for h in (4, 12, 24))
    )
    assert last["market_worker.0.night_sale_available"] == 0
    assert baseline.values["market_worker.1.delivery_slack"] == 0


@pytest.mark.parametrize("arm", ARMS)
def test_information_symmetry_and_immutable_observation(observation, arm):
    obs = copy.deepcopy(observation)
    changed = copy.deepcopy(obs)
    changed.update(seed=10000, future_shops=["YARN_STORE"], reward=1e30)
    changed["farms"][1]["private"] = {"shed": {"MELON": 10000}}
    assert MarketPolicy(arm)(obs) == MarketPolicy(arm)(changed)
    assert market_features(obs).values == market_features(changed).values
    assert obs == observation
    swapped = copy.deepcopy(obs)
    swapped["farms"].reverse()
    swapped["player"] = 1
    assert market_features(obs).values == market_features(swapped).values
    assert MarketPolicy(arm)(obs) == MarketPolicy(arm)(swapped)


def isolated_policy(arm, action=None, opportunity=0, intent="PASS", target=(4, 4)):
    """Isolate intervention tests from unrelated baseline task selection."""
    policy = MarketPolicy(arm)

    class Reference:
        reference = SimpleNamespace(
            last_diagnostics={
                "selected_tasks": [{"unit": 0, "target": target, "intent": intent}],
                "features": {"crop_value": {"MELON": {"net_coins_per_work_action": opportunity}}},
            }
        )

        def __call__(self, obs):
            return {"farmer": action or ["PASS"], "hands": [], "market": []}

    policy.reference = Reference()
    return policy


def test_holding_deadline_night_and_final_turn_force_liquidation(observation):
    obs = copy.deepcopy(observation)
    obs["private"]["shed"]["CARROT"] = 50
    obs["town"]["unlocked_shops"] = ["PET_CAFE"] * 8
    obs["market"]["inventory"]["CARROT"] = 9500
    policy = isolated_policy("01")
    first = policy(obs)
    assert ["SELL", "CARROT", 50] not in first["market"]
    # Apply sales so an already sold lot is never fabricated as still held.
    for order in first["market"]:
        obs["private"]["shed"][order[1]] -= order[2]
    for step in range(1, 5):
        obs.update(step=step, hour=step)
        action = policy(obs)
        for order in action["market"]:
            obs["private"]["shed"][order[1]] -= order[2]
    assert obs["private"]["shed"]["CARROT"] == 0
    # Explicitly exercise an aged lot even if this path chose to sell earlier.
    obs["private"]["shed"]["CARROT"] = 50
    aged = isolated_policy("01")
    aged.first_held["CARROT"] = 0
    assert ["SELL", "CARROT", 50] in aged(obs)["market"]
    for step, hour in ((23, 23), (718, 22)):
        obs.update(step=step, hour=hour)
        assert ["SELL", "CARROT", 50] in isolated_policy("01")(obs)["market"]


def test_delivery_activation_opportunity_cost_and_protected_harvest(observation):
    obs = copy.deepcopy(observation)
    obs.update(step=240, day=10, hour=0)
    obs["private"]["inventories"][0] = {"MELON": 20}
    for y, x in product(range(5), repeat=2):
        tile = game._new_plant("MELON", 0, 24)
        tile.update(yield_units=6, watered_today=True)
        obs["farms"][1]["tiles"][y][x] = tile
    assert isolated_policy("10")(obs)["farmer"] == ["DROP"]
    assert isolated_policy("10", opportunity=1e6)(obs)["farmer"] == ["PASS"]
    assert isolated_policy("10", action=["HARVEST"])(obs)["farmer"] == ["HARVEST"]
    obs["private"]["shed"]["CARROT"] = 95
    assert isolated_policy("10", action=["DROP"])(obs)["farmer"] == ["PLACE", "MELON", 5]


def test_all_off_is_exact_frozen_maturity_baseline_and_history_resets(observation):
    assert MarketPolicy("00")(observation) == RelationshipPolicy("001")(observation)
    policy = MarketPolicy()
    obs = copy.deepcopy(observation)
    policy(obs)
    obs["step"] = 2
    with pytest.raises(ValueError, match="consecutive"):
        policy(obs)
    assert policy(observation) == MarketPolicy()(observation)


def test_urgent_watering_is_protected_and_custom_price_curves_are_rejected(observation):
    obs = copy.deepcopy(observation)
    obs.update(step=718, day=29, hour=22)
    obs["private"]["inventories"][0] = {"MELON": 99}
    obs["farms"][0]["tiles"][4][3] = game._new_plant("MELON", 29, 24)
    policy = isolated_policy("10", action=["WEST"], intent="WATER", target=(3, 4))
    assert policy(obs)["farmer"] == ["WEST"]
    assert policy.last_diagnostics["delivery_decisions"][0]["protected"]
    obs["market"]["params"] = {"MELON": {"base": 999}}
    with pytest.raises(ValueError, match="default price curves"):
        market_features(obs)


def test_factorial_contrast_scaling_and_seed_clustering():
    rows = []
    for seed, seat, arm in product(range(1201, 1207), (0, 1), ARMS):
        a, b = map(int, arm)
        value = seed + seat + 3 * a + 5 * b + 2 * a * b
        rows.append(
            {
                "seed": seed,
                "seat": seat,
                "arm": arm,
                "delivery": a,
                "market_timing": b,
                **{
                    m: value
                    for m in (
                        "coins",
                        "coin_margin",
                        "match_score",
                        "discarded_units",
                        "minimum_observed_cash",
                    )
                },
            }
        )
    frame = pd.DataFrame(rows)
    effects = factorial_summary(frame, 100, 3201)
    selected = effects[effects.metric == "coins"].set_index("contrast")
    assert selected.effect.to_dict() == {
        "delivery": 4,
        "market_timing": 6,
        "delivery:market_timing": 2,
    }
    assert (effects.seed_clusters == 6).all()
    with pytest.raises(ValueError, match="Incomplete"):
        factorial_summary(frame.iloc[:-1], 100, 3201)


def test_full_episode_reproducibility_and_conservation():
    first, second = run_game(43, 0, "11"), run_game(43, 0, "11")
    assert first["semantic_sha256"] == second["semantic_sha256"]
    assert len(first["feature_columns"]) == 933
    assert len(first["feature_samples"]) == 181
    assert first["summary"]["ineffective_farm_actions"] == 0


def test_complete_48_job_pipeline_and_checkpoint_reuse(tmp_path, monkeypatch):
    import kaggriculture_research.market_experiment as experiment

    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/market_research.json").read_text())
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
            **{f: int(bit) for f, bit in zip(FACTORS, arm, strict=True)},
            **{
                m: value
                for m in (
                    "coins",
                    "coin_margin",
                    "match_score",
                    "discarded_units",
                    "minimum_observed_cash",
                )
            },
        }
        payload = {
            "summary": summary,
            "latency_ms": [1.0],
            "feature_extraction_ms": [0.1],
            "feature_schema": {"a": "test", "duplicate": "test", "constant": "test"},
            "feature_columns": ["a", "duplicate", "constant"],
            "feature_samples": [{"step": 0, "values": [value, value, 0]}],
        }
        payload["semantic_sha256"] = experiment.episode_hash(payload)
        return payload

    monkeypatch.setattr(experiment, "run_game", simulated)
    first = experiment.run_experiment(tmp_path, protocol, foundation, Progress(), uploaded.append)
    assert len(calls) == len(uploaded) == first["games"] == 48
    assert first["screening"]["exact_duplicate_groups"] == [["a", "duplicate"]]

    def forbidden(*args):
        raise AssertionError("Valid completed episodes must be reused")

    monkeypatch.setattr(experiment, "run_game", forbidden)
    second = experiment.run_experiment(tmp_path, protocol, foundation, Progress())
    assert second["reused_games"] == 48
    assert first["groups"] == second["groups"]
    invalid = copy.deepcopy(protocol)
    invalid["development_seeds"][0] = foundation["holdout_seeds"][0]
    with pytest.raises(ValueError, match="boundary"):
        experiment.run_experiment(tmp_path, invalid, foundation, Progress())
    invalid = copy.deepcopy(protocol)
    invalid["frozen_sources"]["crop_policy.py"] = "changed"
    with pytest.raises(ValueError, match="Frozen"):
        experiment.run_experiment(tmp_path, invalid, foundation, Progress())
