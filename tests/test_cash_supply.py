"""Cash-bound mechanics and counterexamples, independently checked in the interpreter."""

import copy
import json
import random

import pytest
from test_foundation import initial_observation
from test_market_history import empty_action, transition
from test_market_research import market_state

from kaggriculture_research.cash_history import (
    CashHistory,
    buyable_revenue_upper,
    visible_minimum_spend,
)
from kaggriculture_research.environment import game
from kaggriculture_research.market_history import MarketHistory
from kaggriculture_research.market_policy import MarketPolicy
from kaggriculture_research.supply_policy import SupplyPolicy


@pytest.fixture(scope="module")
def observation():
    return initial_observation()


@pytest.mark.parametrize("item", ("WHEAT", "FERTILIZER"))
def test_buyable_net_cash_envelopes_include_buy_sell_roundtrips(item):
    rng = random.Random(5721)
    for _ in range(400):
        inventory = rng.choice((9800, 9900, 10000, 10050, 10500, 11000))
        own_stock, rival_stock = rng.randrange(101), rng.randrange(101)
        state, env = market_state(item, inventory, own_stock, rival_stock)
        own_orders, rival_orders = [], []
        remaining = own_stock
        for _ in range(rng.randrange(1, 11)):
            quantity = rng.randrange(remaining + 1)
            own_orders.append(["SELL", item, quantity])
            remaining -= quantity
            rival_orders.append([rng.choice(("BUY_PRODUCT", "SELL")), item, rng.randrange(1, 151)])
        if rng.random() < 0.5:
            own_orders = []
        state[0].action["market"], state[1].action["market"] = own_orders, rival_orders
        game._process_market(state, env)
        own_sold = own_stock - state[0].observation.private["shed"][item]
        flow = state[0].observation.market["inventory"][item] - inventory
        upper, identified = buyable_revenue_upper(item, inventory, flow, own_sold)
        actual = state[0].observation.farms[1]["money"] - 3000
        assert actual <= upper
        if identified:
            assert actual == upper


def test_zero_rival_net_trade_can_still_earn_cash_when_we_sell():
    state, env = market_state("FERTILIZER", 10000, 100, 100)
    state[0].action["market"] = [["SELL", "FERTILIZER", 100]]
    state[1].action["market"] = [["SELL", "FERTILIZER", 100], ["BUY_PRODUCT", "FERTILIZER", 100]]
    game._process_market(state, env)
    market = state[0].observation.market
    flow = market["inventory"]["FERTILIZER"] - 10000
    assert flow == 100  # Rival's net product trade is zero.
    actual = state[0].observation.farms[1]["money"] - 3000
    assert actual > 0  # Selling before our supply shock and buying back can profit.
    upper, identified = buyable_revenue_upper("FERTILIZER", 10000, flow, 100)
    assert not identified and upper >= actual


@pytest.mark.parametrize("hidden_seed_buy,expected_lower", ((0, 40), (2, 20)))
def test_public_cash_recovers_floor_sales_without_assuming_no_hidden_buys(
    observation, hidden_seed_buy, expected_lower
):
    obs = copy.deepcopy(observation)
    obs["market"]["inventory"]["MELON"] = 11000
    game._refresh_prices(obs["market"])
    private = game._new_private()
    private["shed"]["MELON"] = 100
    history = CashHistory()
    history.observe(obs)
    history.base.upper["MELON"] = 100
    history._previous_upper["MELON"] = 100
    history.record_action(empty_action())
    orders = [["SELL", "MELON", 40], ["HIRE"]]
    if hidden_seed_buy:
        orders.append(["BUY_SEED", "WHEAT", hidden_seed_buy])
    after, _ = transition(obs, empty_action(), {**empty_action(), "market": orders}, private)
    feature = history.observe(after)
    assert feature.values["cash_history.MELON.sales_lower"] == expected_lower
    assert feature.values["cash_history.minimum_spend"] == 1
    assert 60 <= history.upper["MELON"] == 100 - expected_lower


def test_night_cap_applies_after_the_extra_cash_sale_deduction(observation):
    history = CashHistory()
    obs = copy.deepcopy(observation)
    for step in range(24):
        history.observe(obs)
        if step < 23:
            history.record_action(empty_action())
            obs, _ = transition(obs, empty_action(), empty_action())
    obs["market"]["inventory"]["MELON"] = 11000
    game._refresh_prices(obs["market"])
    history.base.current = copy.deepcopy(obs)
    history.base.upper["MELON"] = history._previous_upper["MELON"] = 150
    history.record_action(empty_action())
    private = game._new_private()
    private["shed"]["MELON"] = 100
    private["inventories"][0]["MELON"] = 50
    rival = {**empty_action(), "market": [["SELL", "MELON", 40]]}
    after, states = transition(obs, empty_action(), rival, private)
    history.observe(after)
    assert states[1].observation.private["shed"]["MELON"] == 100
    assert history.upper["MELON"] == 100


def test_visible_spend_handles_multiple_hires_land_and_night(observation):
    before, after = copy.deepcopy(observation), copy.deepcopy(observation)
    after["farms"][1].update(hires_today=3, unlocked_quadrants=["NW", "NE", "SW"])
    assert visible_minimum_spend(before, after) == 3004
    before["hour"] = 23
    assert visible_minimum_spend(before, after) == 3000


def test_cash_history_contract_prefix_symmetry_and_serialization(observation):
    a, b, loose = CashHistory(), CashHistory(), MarketHistory()
    obs = copy.deepcopy(observation)
    for step in range(30):
        alternative = copy.deepcopy(obs)
        alternative["farms"].reverse()
        alternative["player"] = 1
        alternative.update(seed=9999, future_shops=["YARN_STORE"], reward=1e9)
        alternative["farms"][0]["private"] = {"shed": {"MELON": 99999}}
        features = a.observe(obs)
        assert len(features.values) == 42
        assert features.values == b.observe(alternative).values
        loose.observe(obs)
        assert all(a.upper[p] <= loose.upper[p] for p in a.upper)
        for tracker in (a, b, loose):
            tracker.record_action(empty_action())
        a = CashHistory.from_json(a.to_json())
        if step < 29:
            obs, _ = transition(obs, empty_action(), empty_action())
    assert a.observe(observation).values == CashHistory().observe(observation).values
    bad = {**empty_action(), "market": [["BUY_PRODUCT", "WHEAT", 1]]}
    with pytest.raises(ValueError, match="BUY_PRODUCT"):
        a.record_action(bad)
    payload = json.loads(a.to_json())
    payload["payload"]["previous_upper"]["MELON"] = 999
    with pytest.raises(ValueError, match="checksum"):
        CashHistory.from_json(json.dumps(payload))


@pytest.mark.parametrize("arm,original", (("bank", "10"), ("visible", "11")))
def test_supply_controls_exactly_reproduce_frozen_policy_and_restart(arm, original):
    from kaggriculture_research.environment import make_environment
    from kaggriculture_research.relationship_policy import RelationshipPolicy

    policy, frozen = SupplyPolicy(arm), MarketPolicy(original)
    seen = []

    def actor(obs, config):
        nonlocal policy
        action = policy(obs)
        assert action == frozen(obs)
        seen.append(obs["step"])
        if obs["step"] % 24 == 0:
            policy = SupplyPolicy.from_state_dict(json.loads(json.dumps(policy.state_dict())))
        return action

    env = make_environment(47)
    env.run([actor, RelationshipPolicy("101")])
    assert len(seen) == 719 and all(s.status == "DONE" for s in env.state)
