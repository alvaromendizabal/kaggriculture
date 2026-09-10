"""Observation-safe post-decision price and delivery scenarios.

These are conditional mechanistic descriptors, not forecasts of hidden inventory
or future shops. Visible harvest waves are supply-stress envelopes: they ignore
competition between a rival's workers for jobs, later watering and crop decay.
All calculations target the pinned default game, with at most three hired hands.
"""

from functools import lru_cache
from typing import Any

from kaggriculture_research.crop_policy import distance
from kaggriculture_research.environment import game
from kaggriculture_research.features import PUBLIC_FIELDS, FeatureVector
from kaggriculture_research.relationship_features import (
    ready_units,
    shed_distance,
    town_consumption,
)

HORIZONS = (4, 12, 24)
DEFAULT_MARKET_PARAMS = game.MARKET_PARAMS


@lru_cache(maxsize=65536)
def sale_path(item: str, inventory: int, quantity: int) -> tuple[float, int]:
    """Exact one-sided immediate liquidation, including the non-accumulating floor."""
    if item not in game.PRODUCTS or quantity < 0 or int(quantity) != quantity:
        raise ValueError("Expected a product and a nonnegative integer quantity")
    total = 0.0
    for index in range(quantity):
        price = game.market_price(item, inventory)
        if price == 1:
            return total + quantity - index, inventory
        total += price
        inventory += 1
    return total, inventory


def simultaneous_sale(item: str, inventory: int, own: int, rival: int) -> tuple[float, float, int]:
    """Same-product, same-order-slot concurrent SELL scenario; no other orders."""
    if min(own, rival) < 0 or int(own) != own or int(rival) != rival:
        raise ValueError("Quantities must be nonnegative integers")
    ours = theirs = 0.0
    for index in range(max(own, rival)):
        price = game.market_price(item, inventory)
        ours += price * (index < own)
        theirs += price * (index < rival)
        inventory += (int(index < own) + int(index < rival)) * int(price > 1)
    return ours, theirs, inventory


def project_observation(observation: dict[str, Any]) -> dict[str, Any]:
    obs = {key: observation[key] for key in PUBLIC_FIELDS}
    if obs["player"] not in (0, 1) or len(obs["farms"]) != 2:
        raise ValueError("Expected two public farms")
    if game._resolve_market_params(obs["market"].get("params")) != DEFAULT_MARKET_PARAMS:
        raise ValueError("Market scenarios require the registered default price curves")
    if any(len(farm["hands"]) > 3 for farm in obs["farms"]):
        raise ValueError("This fixed-schema study supports at most three hired hands")
    return obs


def visible_wave(obs: dict, player: int) -> dict[str, list[tuple[int, int]]]:
    """Currently visible harvestable units with optimistic delivery-delay envelopes.

    Delta 0 is the current market phase. A harvest at a shed-access tile can
    first be deposited and sold on delta 1. Nightly deposits can be sold only
    on the following callback. Current workers are not extrapolated past expiry.
    """
    farm = obs["farms"][player]
    positions = [farm["farmer"], *farm["hands"]]
    wave = {item: [] for item in game.PRODUCTS}
    until_night = 24 - obs["hour"]
    for y, row in enumerate(farm["tiles"]):
        for x, tile in enumerate(row):
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                item, units = tile["crop"], ready_units(tile, obs["day"])
            elif tile.get("animal") in game.ANIMALS:
                item = game.ANIMALS[tile["animal"]]["product"]
                units = tile.get("yield_units", 0)
            else:
                continue
            if units <= 0:
                continue
            travel = min(distance(position, (x, y)) for position in positions)
            delay = 719
            if travel + 1 <= until_night:
                delay = min(travel + shed_distance((x, y)) + 1, until_night)
            wave[item].append((int(units), delay))
    return wave


def wave_units(wave: dict, item: str, delay: int) -> int:
    return sum(units for units, earliest in wave[item] if earliest <= delay)


def two_stage_value(
    item: str, inventory: int, quantity: int, sell_now: int, demand: int, rival_supply: int
) -> tuple[float, float]:
    """Sell a prefix now, then liquidate the rest after a conditional market path.

    Quiet path: own prefix -> known town consumption -> remaining own sale.
    Stress path: own prefix -> rival wave -> known consumption -> remaining sale.
    The second path is a defined scenario, not exact unknown trade-event timing.
    """
    if not 0 <= sell_now <= quantity or min(demand, rival_supply) < 0:
        raise ValueError("Invalid post-decision scenario")
    revenue, post = sale_path(item, inventory, sell_now)
    quiet = revenue + sale_path(item, post - demand, quantity - sell_now)[0]
    _, stressed = sale_path(item, post, rival_supply)
    stress = revenue + sale_path(item, stressed - demand, quantity - sell_now)[0]
    return quiet, stress


def liquidation_scenarios(obs: dict, item: str, quantity: int, delay: int, wave: dict) -> tuple:
    demand = town_consumption(obs["town"]["unlocked_shops"], item, obs["step"], delay)
    return two_stage_value(
        item, obs["market"]["inventory"][item], quantity, 0, demand, wave_units(wave, item, delay)
    )


def market_features(observation: dict[str, Any]) -> FeatureVector:
    obs = project_observation(observation)
    ours, rival = visible_wave(obs, obs["player"]), visible_wave(obs, 1 - obs["player"])
    private, market = obs["private"], obs["market"]
    result = FeatureVector()
    for item in game.PRODUCTS:
        own_ready = sum(n for n, _ in ours[item])
        rival_ready = sum(n for n, _ in rival[item])
        held = private["shed"].get(item, 0)
        carried = sum(inv.get(item, 0) for inv in private["inventories"])
        quantity = min(100, held + carried + own_ready)
        inventory = market["inventory"][item]
        immediate = sale_path(item, inventory, quantity)[0]
        basic = {
            "own_ready_units": own_ready,
            "rival_ready_units": rival_ready,
            "shed_units": held,
            "carried_units": carried,
            "conditional_quantity": quantity,
            "rival_earliest_delivery": min((t for _, t in rival[item]), default=719),
            "immediate_revenue": immediate,
        }
        for name, value in basic.items():
            result.add(f"market_plan.{item}.{name}", value, "post_decision_inventory")
        for horizon in HORIZONS:
            available = obs["step"] + horizon <= 718
            demand = town_consumption(obs["town"]["unlocked_shops"], item, obs["step"], horizon)
            quiet, stress = liquidation_scenarios(obs, item, quantity, horizon, rival)
            values = {
                "available": int(available),
                "known_demand": demand,
                "demand_only_inventory": inventory - demand,
                "demand_only_price": game.market_price(item, inventory - demand),
                "quiet_revenue": quiet,
                "rival_stress_revenue": stress,
                "rival_penalty": quiet - stress,
                "quiet_holding_premium": quiet - immediate,
            }
            for name, value in values.items():
                result.add(
                    f"market_plan.{item}.h{horizon}.{name}",
                    value if available else 0,
                    "conditional_market_paths",
                )
    farm = obs["farms"][obs["player"]]
    positions = [farm["farmer"], *farm["hands"]]
    all_carry = sum(sum(inv.values()) for inv in private["inventories"])
    night_delay = 24 - obs["hour"]
    night_available = obs["step"] + night_delay <= 718
    for index in range(4):
        present = index < len(positions)
        inventory = private["inventories"][index] if present else {}
        revenue = quiet = stress = 0.0
        for item, amount in inventory.items():
            if item in game.PRODUCTS:
                revenue += sale_path(item, market["inventory"][item], amount)[0]
                quiet_value, stress_value = liquidation_scenarios(
                    obs, item, amount, night_delay, rival
                )
                quiet += quiet_value
                stress += stress_value
        actions = shed_distance(positions[index]) + 1 if present else 0
        values = {
            "present": int(present),
            "carried_units": sum(inventory.values()),
            "delivery_actions": actions,
            "delivery_slack": min(719 - obs["step"], night_delay) - actions,
            "liquidation_revenue": revenue,
            "quiet_night_revenue": quiet if night_available else 0,
            "rival_stress_night_revenue": stress if night_available else 0,
            "night_sale_available": int(night_available),
            "overflow_after_sell_all": max(0, all_carry - 100),
        }
        for name, value in values.items():
            result.add(
                f"market_worker.{index}.{name}",
                value if present else 0,
                "delivery_opportunity_cost",
            )
    return result
