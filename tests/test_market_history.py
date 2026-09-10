"""Public-history parity, ambiguity, availability, replay and serialization tests."""

import copy
import importlib.util
import json
import shutil
from itertools import product
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_foundation import initial_observation

from kaggriculture_research.environment import game
from kaggriculture_research.market_history import (
    BOUNDED_PRODUCTS,
    MarketHistory,
    own_nonbuyable_sales,
    possible_collection,
)


@pytest.fixture(scope="module")
def observation():
    return initial_observation()


def empty_action():
    return {"farmer": ["PASS"], "hands": [], "market": []}


def transition(obs, own, rival, rival_private=None):
    """Evaluator-only official one-turn transition, without hidden state in features."""
    copied = copy.deepcopy(obs)
    farms, market, town = copied["farms"], copied["market"], copied["town"]
    states = []
    for seat in (0, 1):
        private = (
            copied["private"]
            if seat == copied["player"]
            else copy.deepcopy(rival_private or game._new_private())
        )
        states.append(
            SimpleNamespace(
                observation=SimpleNamespace(
                    farms=farms,
                    market=market,
                    town=town,
                    private=private,
                    step=copied["step"],
                    player=seat,
                ),
                action=own if seat == copied["player"] else rival,
            )
        )
    env = SimpleNamespace(
        configuration=SimpleNamespace(episodeSteps=720), done=False, info={"seed": 41}
    )
    game.interpreter(states, env)
    step = copied["step"] + 1
    copied.update(step=step, day=step // 24, hour=step % 24)
    return copied, states


def value(features, item, name):
    return features.values[f"market_history.{item}.last.{name}"]


def test_fixed_schema_masks_and_empty_initial_stock(observation):
    features = MarketHistory().observe(observation)
    assert len(features.values) == 333
    for item in game.PRODUCTS:
        assert value(features, item, "available") == 0
        assert value(features, item, "sales_identified") == 0
        assert value(features, item, "stock_upper") == 0
        assert value(features, item, "sale_supported") == int(item in BOUNDED_PRODUCTS)


def test_duplicate_shops_and_center_use_previous_phase(observation):
    obs = copy.deepcopy(observation)
    obs["town"]["unlocked_shops"] = ["PET_CAFE", "PET_CAFE"]
    history = MarketHistory()
    history.observe(obs)
    history.record_action(empty_action())
    after, _ = transition(obs, empty_action(), empty_action())
    after["town"]["unlocked_shops"].append("PET_CAFE")
    features = history.observe(after)
    assert value(features, "CARROT", "known_demand") == 5
    assert value(features, "CARROT", "trade_net") == 0
    assert value(features, "CARROT", "sales_upper") == 0


@pytest.mark.parametrize("item", BOUNDED_PRODUCTS)
def test_nonbuyable_sale_bounds_match_official_market_including_floor(observation, item):
    for stock, own_quantity, rival_quantity, inventory in product(
        (0, 20, 100), (0, 20), (0, 1, 100), (9900, 10000, 1000000)
    ):
        obs = copy.deepcopy(observation)
        obs["market"]["inventory"][item] = inventory
        game._refresh_prices(obs["market"])
        obs["private"]["shed"][item] = own_quantity
        private = game._new_private()
        private["shed"][item] = stock
        own, rival = empty_action(), empty_action()
        own["market"] = [["SELL", item, own_quantity]]
        rival["market"] = [["SELL", item, rival_quantity]]
        history = MarketHistory()
        history.observe(obs)
        history.upper[item] = stock  # Known test-fixture bound, never an evaluator input in replay.
        history.record_action(own)
        after, states = transition(obs, own, rival, private)
        features = history.observe(after)
        actual = stock - states[1].observation.private["shed"][item]
        assert (
            value(features, item, "sales_lower") <= actual <= value(features, item, "sales_upper")
        )
        assert value(features, item, "stock_upper") >= stock - actual
        if value(features, item, "sales_identified"):
            assert value(features, item, "sales_lower") == actual


def ripe_state(observation, item="MELON", workers=1, step=240):
    obs = copy.deepcopy(observation)
    obs.update(step=step, day=step // 24, hour=step % 24)
    tile = game._new_plant(item, 0, 24)
    tile.update(yield_units=3, watered_today=False, consecutive_unwatered=0)
    obs["farms"][1]["tiles"][4][4] = tile
    obs["farms"][1]["farmer"] = [4, 4]
    obs["farms"][1]["hands"] = [[4, 4] for _ in range(workers - 1)]
    return obs


def test_disappearance_is_an_upper_bound_not_harvest_identification(observation):
    before = ripe_state(observation)
    for op in ("DIG", "HARVEST"):
        after, _ = transition(before, empty_action(), {**empty_action(), "farmer": [op]})
        assert possible_collection(before, after)["MELON"] == 3
    after, _ = transition(before, empty_action(), empty_action())
    assert possible_collection(before, after)["MELON"] == 0


def test_colocated_fertilize_water_harvest_and_single_worker_limit(observation):
    before = ripe_state(observation, workers=3)
    private = game._new_private()
    private["inventories"] = [{"FERTILIZER": 1}, {}, {}]
    rival = {"farmer": ["FERTILIZE"], "hands": [["WATER"], ["HARVEST"]], "market": []}
    after, states = transition(before, empty_action(), rival, private)
    assert states[1].observation.private["inventories"][2]["MELON"] == 5
    assert possible_collection(before, after)["MELON"] == 5
    before = ripe_state(observation, workers=1)
    after, _ = transition(before, empty_action(), {**empty_action(), "farmer": ["HARVEST"]})
    assert possible_collection(before, after)["MELON"] == 3


@pytest.mark.parametrize("item", ("TOMATO", "STRAWBERRY"))
def test_ongoing_harvest_and_night_regeneration_do_not_erase_collection(observation, item):
    for step in (240, 263):
        before = ripe_state(observation, item=item, step=step)
        before["farms"][1]["tiles"][4][4]["watered_today"] = True
        rival = {**empty_action(), "farmer": ["HARVEST"]}
        after, _ = transition(before, empty_action(), rival)
        assert possible_collection(before, after)[item] == 3


def test_own_sales_repeated_orders_truncation_and_atomic_seed_blocking(observation):
    obs = copy.deepcopy(observation)
    obs["private"]["shed"]["CARROT"] = 8
    obs["private"]["inventories"] = [{"CARROT": 5}, {}]
    obs["private"]["seeds"]["WHEAT"] = 1
    obs["farms"][0]["hands"] = [[3, 4]]
    action = {
        "farmer": ["DROP"],
        "hands": [["PASS"]],
        "market": [["SELL", "CARROT", 3], ["SELL", "CARROT", 20]],
    }
    assert own_nonbuyable_sales(obs, action)["CARROT"] == 13
    action["market"] = [["HIRE"]] * 10 + [["SELL", "CARROT", 100]]
    assert own_nonbuyable_sales(obs, action)["CARROT"] == 0
    action.update(farmer=["PLANT", "WHEAT"], hands=[["PLANT", "WHEAT"]], market=[])
    original = copy.deepcopy(obs)
    assert all(n == 0 for n in own_nonbuyable_sales(obs, action).values())
    assert obs == original


def test_history_rejects_skips_missing_actions_player_changes_and_cold_start(observation):
    history = MarketHistory()
    history.observe(observation)
    after, _ = transition(observation, empty_action(), empty_action())
    with pytest.raises(ValueError, match="consecutive"):
        history.observe(after)
    history.record_action(empty_action())
    with pytest.raises(ValueError, match="exactly one"):
        history.record_action(empty_action())
    skipped = copy.deepcopy(after)
    skipped.update(step=2, hour=2)
    with pytest.raises(ValueError, match="consecutive"):
        history.observe(skipped)
    switched = copy.deepcopy(after)
    switched["player"] = 1
    with pytest.raises(ValueError, match="consecutive"):
        history.observe(switched)
    with pytest.raises(ValueError, match="callback zero"):
        MarketHistory().observe(after)
    history.observe(after)


def test_prefix_serialization_symmetry_extraneous_metadata_and_reset(observation):
    history, swapped, poisoned = MarketHistory(), MarketHistory(), MarketHistory()
    obs = copy.deepcopy(observation)
    for step in range(30):
        clean = copy.deepcopy(obs)
        alternative = copy.deepcopy(obs)
        alternative["farms"].reverse()
        alternative["player"] = 1
        extra = copy.deepcopy(obs)
        extra.update(
            seed=12345,
            reward=999999,
            future_shops=["YARN_STORE"],
            opponent_action={"market": [["SELL", "MELON", 99]]},
        )
        extra["farms"][1]["private"] = {"shed": {"MELON": 999999}}
        expected = history.observe(obs)
        assert (
            expected.values == swapped.observe(alternative).values == poisoned.observe(extra).values
        )
        assert obs == clean
        assert history.to_json() == poisoned.to_json()
        history = MarketHistory.from_json(history.to_json())
        for tracker in (history, swapped, poisoned):
            tracker.record_action(empty_action())
        history = MarketHistory.from_json(history.to_json())
        if step < 29:
            obs, _ = transition(obs, empty_action(), empty_action())
    assert expected.values["market_history.MELON.w24.observed"] == 24
    assert history.observe(observation).values == MarketHistory().observe(observation).values
    state = json.loads(history.to_json())
    state["payload"]["upper"]["MELON"] = 1000
    with pytest.raises(ValueError, match="checksum"):
        MarketHistory.from_json(json.dumps(state))


@pytest.mark.parametrize("item", ("WHEAT", "FERTILIZER"))
def test_buyable_goods_have_net_flow_not_fabricated_gross_sale_bounds(observation, item):
    history = MarketHistory()
    history.observe(observation)
    history.record_action(empty_action())
    rival = {**empty_action(), "market": [["BUY_PRODUCT", item, 1]]}
    after, _ = transition(observation, empty_action(), rival)
    features = history.observe(after)
    assert value(features, item, "trade_net") == -1
    assert value(features, item, "sale_supported") == 0
    assert value(features, item, "sales_identified") == 0
    assert value(features, item, "stock_upper") == 0


@pytest.mark.parametrize(
    "corruption", ("none", "source", "counts", "groups", "selection", "duplicates")
)
def test_published_history_verifier_rejects_stale_or_inconsistent_evidence(tmp_path, corruption):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "history_verifier", root / "scripts/verify_market_history.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    paths = (
        "reports/market_history_research.json",
        "reports/market_research.json",
        "scripts/analyze_market_history.py",
        "src/kaggriculture_research/market_history.py",
    )
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, target)
    report_path = tmp_path / paths[0]
    report = json.loads(report_path.read_text())
    if corruption == "source":
        (tmp_path / paths[2]).write_text("# incompatible analysis\n")
    elif corruption == "counts":
        report["constant_features"] += 1
    elif corruption == "groups":
        report["groups"][0]["gross_sale_units"] += 1
    elif corruption == "selection":
        report["retained_features"] = 1
    elif corruption == "duplicates":
        report["exact_nonconstant_duplicate_groups"][0].append("unknown_column")
    report_path.write_text(json.dumps(report))
    if corruption == "none":
        assert module.verify_history(tmp_path)["history_features"] == 333
    else:
        with pytest.raises(ValueError):
            module.verify_history(tmp_path)
