"""Mechanistic relationships, not an indiscriminate polynomial feature expansion.

Only current legal observations and an explicitly reset, causal 24-turn history
are inputs. Prices and inventory projections are conditional scenarios. No future
shops, opponent inventory, simulation seed or evaluator outcome is consulted.
The refresh helpers predict that phase ONLY, excluding preceding in-turn decay.
"""

import math
from collections import Counter, deque
from typing import Any

from kaggriculture_research.crop_policy import SHED, distance, water_features
from kaggriculture_research.environment import game
from kaggriculture_research.features import FeatureVector, sale_revenue


def shed_distance(position: list | tuple) -> int:
    return min(distance(position, point) for point in SHED)


def ready_units(tile: Any, day: int) -> int:
    if not isinstance(tile, dict):
        return 0
    if tile.get("kind") == "PLANT":
        if day - tile["planted_day"] < game.CROPS[tile["crop"]]["first_yield_day"]:
            return 0
    elif not tile.get("animal"):
        return 0
    return tile["yield_units"]


def capped_ready(tile: Any, day: int) -> bool:
    if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
        return False
    p = game.CROPS[tile["crop"]]
    return not p["ongoing"] and ready_units(tile, day) >= p["max_yield"]


def plant_refresh(tile: dict, day: int, water: bool = False, fertilize: bool = False) -> dict:
    """Hypothetical WATER/FERTILIZE then next refresh, with no preceding decay.

    Treatment inputs assume an available worker/item; they are not executable
    action bundles. For single-yield crops FERTILIZE precedes WATER in this
    counterfactual, and has no retroactive effect if already watered today.
    """
    p = game.CROPS[tile["crop"]]
    age = day - tile["planted_day"]
    amount = tile["yield_units"]
    watered = tile["watered_today"] or water
    fertile = tile["fertilized_until_day"] >= day or fertilize
    if water and not tile["watered_today"] and not p["ongoing"]:
        if (p["max_yield_day"] + 1) // 2 <= age <= p["max_yield_day"]:
            amount = min(p["max_yield"], amount + (2 if fertile else 1))
    dead = not watered and tile["consecutive_unwatered"] + 1 >= 2
    if dead:
        return {"dead": True, "units": 0, "production_due": False}
    offset = age + 1 - p["first_yield_day"]
    due = bool(
        p["ongoing"]
        and offset >= 0
        and offset % p["interval"] == 0
        and offset // p["interval"] < p["max_yield"]
    )
    if due:
        amount = min(p["max_yield"], amount + (2 if watered and fertile else 1))
    return {"dead": False, "units": amount, "production_due": due}


def animal_refresh(tile: dict, day: int, feed: bool = False, care: bool = False) -> dict:
    """Next refresh, including survival, yield cap and delayed care-bank ordering."""
    p = game.ANIMALS[tile["animal"]]
    fed, cared = tile["fed_today"] or feed, tile["cared_today"] or care
    if not fed and tile["consecutive_unfed"] + 1 >= 2:
        return {"escaped": True, "units": 0, "bank": 0, "production_due": False}
    offset = day + 1 - tile["placed_day"] - p["first_yield_day"]
    due = offset >= 0 and offset % p["interval"] == 0
    bank, amount = tile["pending_care_bonus"], tile["yield_units"]
    if due:
        amount = min(p["max_held"], amount + 1 + (bank if fed else 0))
        bank = 0
    # Today's care is banked AFTER today's production, never paid retroactively.
    bank += int(fed and cared)
    return {"escaped": False, "units": amount, "bank": bank, "production_due": due}


def town_consumption(shops: list[str], item: str, step: int, horizon: int) -> int:
    """Known-shop demand at actions step..step+horizon-1; no future unlocks."""
    if horizon < 0:
        raise ValueError("Negative scenario horizon")
    each = sum(2 if len(game.SHOPS[s]) == 1 else 1 for s in shops if item in game.SHOPS[s])
    shop_events = (step + horizon - 1) // 4 - (step - 1) // 4
    center_events = (step + horizon - 1) // 24 - (step - 1) // 24
    return each * shop_events + int(item in game.TOWN_CENTER_PRODUCTS) * center_events


def cash_reserve(observation: dict, max_hands: int = 3) -> dict[str, float]:
    """Conservative staffing runway to earliest crop maturity, not optimal capital.

    All bounded hands are budgeted daily; no forecast sales are spendable cash.
    Maturity ignores future death and water quality, so this is an explicit
    working-capital scenario, not a guarantee of the next receipt date.
    """
    farm = observation["farms"][observation["player"]]
    day, hour, step = observation["day"], observation["hour"], observation["step"]
    waits = []
    for y, row in enumerate(farm["tiles"]):
        for x, tile in enumerate(row):
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                days = max(
                    0, tile["planted_day"] + game.CROPS[tile["crop"]]["first_yield_day"] - day
                )
                waits.append(max(0, days * 24 - hour) + shed_distance((x, y)) + 2)
    wait = min(waits, default=24)
    days = min(math.ceil(max(0, 719 - step) / 24), max(1, math.ceil(wait / 24)))
    daily = sum(game._hire_cost(n) for n in range(max_hands))
    today = sum(game._hire_cost(n) for n in range(farm["hires_today"], max_hands))
    reserve = daily * days + today
    return {
        "receipt_wait_scenario_actions": wait,
        "staffing_days_scenario": days,
        "daily_full_staff_cost": daily,
        "labor_reserve": reserve,
        "seed_spendable_cash": max(0, farm["money"] - reserve),
        "cash_to_reserve_ratio": farm["money"] / max(1, reserve),
        "reserve_shortfall": max(0, reserve - farm["money"]),
    }


def inventory_pressure(observation: dict) -> dict[str, float]:
    """Distinguish DROP-before-sales from nightly deposit-after-sales capacity."""
    private = observation["private"]
    farm = observation["farms"][observation["player"]]
    shed = sum(private["shed"].values())
    carried = sum(sum(inv.values()) for inv in private["inventories"])
    nonsellable = sum(n for c, n in private["shed"].items() if c not in game.PRODUCTS)
    ready = sum(ready_units(t, observation["day"]) for row in farm["tiles"] for t in row)
    return {
        "free_before_market": max(0, 100 - shed),
        "free_after_sell_all": max(0, 100 - nonsellable),
        "night_overflow_if_pass": max(0, shed + carried - 100),
        "night_overflow_after_sell_all": max(0, nonsellable + carried - 100),
        "ready_wave_overflow_after_sell_all": max(0, nonsellable + carried + ready - 100),
        "carried_plus_ready_units": carried + ready,
        "ready_wave_units": ready,
        "nonsellable_capacity_lock": nonsellable,
        "carry_fraction_of_capacity": carried / 100,
    }


def relationship_features(observation: dict[str, Any]) -> FeatureVector:
    """Fixed schema for the official 10x10, 719-action, <=3-hand research setting."""
    obs, f = observation, FeatureVector()
    day, hour, step = obs["day"], obs["hour"], obs["step"]
    remaining = max(0, 719 - step)
    own = obs["farms"][obs["player"]]
    private, market = obs["private"], obs["market"]
    if any(
        len(farm["tiles"]) != 10 or any(len(r) != 10 for r in farm["tiles"])
        for farm in obs["farms"]
    ):
        raise ValueError("Relationships require official 10x10 boards")
    if len(own["hands"]) > 3 or len(private["inventories"]) != len(own["hands"]) + 1:
        raise ValueError("Relationship worker schema is bounded at three hands")
    for item in game.PRODUCTS:
        if market["prices"][item] != game.market_price(item, market["inventory"][item]):
            raise ValueError("Relationships require pinned market curves")

    def add(prefix: str, values: dict, family: str) -> None:
        for name, value in values.items():
            f.add(prefix + "." + name, value, family)

    pressure = inventory_pressure(obs)
    add("storage", pressure, "storage_interactions")
    add("capital", cash_reserve(obs), "cashflow")
    positions = [own["farmer"], *own["hands"]]
    for i in range(4):
        active = i < len(positions)
        inv = private["inventories"][i] if active else {}
        dist = shed_distance(positions[i]) if active else 0
        amount = sum(inv.values())
        value = sum(
            sale_revenue(c, market["inventory"][c], n) for c, n in inv.items() if c in game.PRODUCTS
        )
        add(
            f"delivery.unit{i}",
            {
                "active": active,
                "shed_distance": dist,
                "carried_units": amount,
                "conditional_sale_value": value,
                "dump_loss_before_market": max(0, amount - pressure["free_before_market"]),
                "delivery_refresh_slack": (24 - hour - dist - 1) if active else 0,
                "delivery_terminal_slack": (remaining - dist - 1) if active else 0,
                "value_per_delivery_action": value / (dist + 1),
            },
            "delivery_feasibility",
        )

    supply = {side: Counter() for side in ("own", "opponent")}
    for side, farm in (("own", own), ("opponent", obs["farms"][1 - obs["player"]])):
        workers = [farm["farmer"], *farm["hands"]]
        located = [
            (x, y, t)
            for y, row in enumerate(farm["tiles"])
            for x, t in enumerate(row)
            if isinstance(t, dict)
        ]
        for crop, p in game.CROPS.items():
            group = [(x, y, t) for x, y, t in located if t.get("crop") == crop]
            totals = Counter()
            maturity, decay, route = [], [], []
            for x, y, tile in group:
                age = day - tile["planted_day"]
                units = ready_units(tile, day)
                supply[side][crop] += units
                dist = min(distance(w, (x, y)) for w in workers)
                bank_actions = dist + 1 + shed_distance((x, y)) + 1
                maturity.append(max(0, (p["first_yield_day"] - age) * 24 - hour))
                if tile["max_lifespan_step"] >= 0:
                    decay.append(max(0, tile["max_lifespan_step"] - step))
                route.append(dist)
                base = plant_refresh(tile, day)
                watered = plant_refresh(tile, day, water=True)
                treated = plant_refresh(tile, day, water=True, fertilize=True)
                totals.update(
                    {
                        "capped_ready_tiles": int(capped_ready(tile, day)),
                        "avoidable_wait_unit_days": units * max(0, p["max_yield_day"] - age)
                        if capped_ready(tile, day)
                        else 0,
                        "water_now_increment_units": water_features(tile, day, hour)[
                            "water_bonus_units"
                        ],
                        "refresh_yield_saved_by_water": watered["units"] - base["units"],
                        "refresh_increment_from_fertilizer_given_water": treated["units"]
                        - watered["units"],
                        "next_refresh_production_events": int(watered["production_due"]),
                        "ready_units_with_active_delivery_route": units
                        if bank_actions <= min(remaining, 24 - hour)
                        else 0,
                        "ready_units_without_terminal_route": units
                        if bank_actions > remaining
                        else 0,
                        "water_death_tasks_unreachable_today": int(
                            base["dead"] and dist + 1 > 24 - hour
                        ),
                        "decay_within_two_actions": int(0 <= tile["max_lifespan_step"] - step <= 2),
                    }
                )
            names = (
                "capped_ready_tiles",
                "avoidable_wait_unit_days",
                "water_now_increment_units",
                "refresh_yield_saved_by_water",
                "refresh_increment_from_fertilizer_given_water",
                "next_refresh_production_events",
                "ready_units_with_active_delivery_route",
                "ready_units_without_terminal_route",
                "water_death_tasks_unreachable_today",
                "decay_within_two_actions",
            )
            add(
                f"{side}.timing.{crop}",
                {
                    **{n: totals[n] for n in names},
                    "present": bool(group),
                    "first_maturity_actions": min(maturity, default=719),
                    "known_decay_present": bool(decay),
                    "first_decay_actions": min(decay, default=719),
                    "mean_worker_distance": sum(route) / max(1, len(route)),
                },
                "crop_resource_timing",
            )
        for animal, p in game.ANIMALS.items():
            group = [t for _, _, t in located if t.get("animal") == animal]
            totals = Counter()
            for tile in group:
                supply[side][p["product"]] += ready_units(tile, day)
                base = animal_refresh(tile, day)
                fed = animal_refresh(tile, day, feed=True)
                cared = animal_refresh(tile, day, feed=True, care=True)
                totals.update(
                    {
                        "escape_prevented_by_feed": int(base["escaped"]),
                        "refresh_units_saved_by_feed": fed["units"] - base["units"],
                        "care_bank_marginal": cared["bank"] - fed["bank"],
                        "next_production_events": int(fed["production_due"]),
                        "cap_headroom": p["max_held"] - tile["yield_units"],
                        "banked_bonus_at_risk_if_unfed": tile["pending_care_bonus"]
                        if not tile["fed_today"] and fed["production_due"]
                        else 0,
                        "next_fed_production_saturation": max(
                            0, tile["yield_units"] + 1 + tile["pending_care_bonus"] - p["max_held"]
                        )
                        if fed["production_due"]
                        else 0,
                    }
                )
            add(
                f"{side}.husbandry.{animal}",
                {
                    n: totals[n]
                    for n in (
                        "escape_prevented_by_feed",
                        "refresh_units_saved_by_feed",
                        "care_bank_marginal",
                        "next_production_events",
                        "cap_headroom",
                        "banked_bonus_at_risk_if_unfed",
                        "next_fed_production_saturation",
                    )
                },
                "animal_feed_care_interactions",
            )

    for item in game.PRODUCTS:
        inv = market["inventory"][item]
        held = private["shed"].get(item, 0) + sum(x.get(item, 0) for x in private["inventories"])
        wave = held + supply["own"][item]
        revenue = sale_revenue(item, inv, wave)
        demand = town_consumption(obs["town"]["unlocked_shops"], item, step, min(24, remaining))
        price_demand = game.market_price(item, inv - demand)
        # Opponent standing harvestable supply is visible, not their private stock.
        after_visible_rival = inv + supply["opponent"][item]
        add(
            f"pressure.{item}",
            {
                "own_held_and_ready_wave": wave,
                "opponent_visible_ready_units": supply["opponent"][item],
                "wave_conditional_revenue": revenue,
                "wave_average_price": revenue / max(1, wave),
                "wave_price_impact_cost": wave * market["prices"][item] - revenue,
                "known_demand_next_day": demand,
                "demand_only_next_day_price_change": price_demand - market["prices"][item],
                "wave_minus_known_day_demand": wave - demand,
                "visible_rival_supply_stress_price": game.market_price(item, after_visible_rival),
                "wave_revenue_after_rival_supply_stress": sale_revenue(
                    item, after_visible_rival, wave
                ),
            },
            "market_supply_demand_interactions",
        )
    add(
        "interactions",
        {
            "water_bonus_under_overflow_pressure": sum(
                v
                for n, v in f.values.items()
                if n.startswith("own.timing.") and n.endswith("water_now_increment_units")
            )
            * int(pressure["ready_wave_overflow_after_sell_all"] > 0),
            "capacity_pressure_per_worker": pressure["ready_wave_overflow_after_sell_all"]
            / len(positions),
            "ready_units_per_worker_turn_today": pressure["ready_wave_units"]
            / max(1, len(positions) * (24 - hour)),
            "terminal_carry_at_risk": sum(
                sum(private["inventories"][i].values())
                for i, p in enumerate(positions)
                if shed_distance(p) + 1 > remaining
            ),
        },
        "cross_resource_interactions",
    )
    return f


class CausalHistory:
    """One instance per episode/player; exactly known lags, never padded as data."""

    def __init__(self) -> None:
        self.history: deque[dict] = deque(maxlen=25)
        self.player: int | None = None

    def observe(self, observation: dict) -> FeatureVector:
        step, player = observation["step"], observation["player"]
        if self.history and (player != self.player or step != self.history[-1]["step"] + 1):
            raise ValueError("History requires consecutive observations from one episode/player")
        self.player = player
        current = {
            "step": step,
            "cash": observation["farms"][player]["money"],
            "inventory": dict(observation["market"]["inventory"]),
            "prices": dict(observation["market"]["prices"]),
        }
        f = FeatureVector()
        for lag in (1, 24):
            available = len(self.history) >= lag
            prior = self.history[-lag] if available else current
            f.add(f"history.lag{lag}.available", available, "causal_market_history")
            f.add(
                f"history.lag{lag}.cash_change",
                current["cash"] - prior["cash"],
                "causal_market_history",
            )
            for item in game.PRODUCTS:
                f.add(
                    f"history.lag{lag}.{item}.inventory_change",
                    current["inventory"][item] - prior["inventory"][item],
                    "causal_market_history",
                )
                f.add(
                    f"history.lag{lag}.{item}.price_log_change",
                    math.log(current["prices"][item] / prior["prices"][item]),
                    "causal_market_history",
                )
        self.history.append(current)
        return f
