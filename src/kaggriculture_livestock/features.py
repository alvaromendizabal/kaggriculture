"""Legal-observation resource features and explicitly conditional short rollouts.

No learned continuation values, hidden state, future shops or opponent actions.
The 42 earlier cash-bound features are outside their own-sale-only contract here.
"""

import json
import math
from functools import lru_cache

from kaggriculture_research.crop_policy import SHED, distance
from kaggriculture_research.environment import game
from kaggriculture_research.features import FeatureVector, sale_revenue
from kaggriculture_research.market_features import project_observation
from kaggriculture_research.relationship_features import animal_refresh, ready_units

WORK_VALUE = 8.0  # Fixed scenario opportunity charge, never an actual cash deduction.
PLANT_HORIZON = 7 * 24


def located(farm: dict) -> list[tuple[int, int, dict]]:
    return [
        (x, y, tile)
        for y, row in enumerate(farm["tiles"])
        for x, tile in enumerate(row)
        if isinstance(tile, dict)
    ]


def product_totals(private: dict) -> dict[str, int]:
    return {
        item: sum(inv.get(item, 0) for inv in [private["shed"], *private["inventories"]])
        for item in game.PRODUCTS
    }


def purchase_cost(item: str, inventory: int, units: int) -> float:
    """Exact isolated BUY quote path; concurrent rival orders can change execution."""
    if item not in ("WHEAT", "FERTILIZER") or units < 0:
        raise ValueError("Unsupported purchase scenario")
    return float(sum(game.market_price(item, inventory - k) for k in range(1, units + 1)))


def next_production_day(tile: dict, earliest: int) -> int:
    p = game.ANIMALS[tile["animal"]]
    first = tile["placed_day"] + p["first_yield_day"]
    return first + max(0, math.ceil((earliest - first) / p["interval"])) * p["interval"]


def animal_service(tile: dict, obs: dict, position: tuple[int, int]) -> dict[str, float]:
    """Feed/CARE values distinguish next refresh from later bonus conversion.

    Care's future conversion assumes survival, feeding on the conversion day and
    collection before capacity binds. Separate conservative no-collection headroom
    is exposed; neither scenario is a probability forecast or a route guarantee.
    """
    p = game.ANIMALS[tile["animal"]]
    day, step = obs["day"], obs["step"]
    production = next_production_day(tile, day + 1)
    care_day = next_production_day(tile, day + 2)
    due = production == day + 1
    baseline = animal_refresh(tile, day)
    fed = animal_refresh(tile, day, feed=True)
    bank = 0 if due else tile["pending_care_bonus"]
    room = max(0, p["max_held"] - 1 - bank)
    no_collection_room = max(0, room - tile["yield_units"])
    delivery = min(distance(position, s) for s in SHED)
    care_bankable = care_day * 24 + 1 + delivery + 1 <= 718
    care_units = int(not tile["cared_today"] and room > 0 and care_bankable)
    quote = game.market_price(p["product"], obs["market"]["inventory"][p["product"]])
    return {
        "present": 1,
        "feed_due": int(not tile["fed_today"]),
        "escape_without_feed": int(baseline["escaped"]),
        "stored_units_at_escape_risk": tile["yield_units"] * int(baseline["escaped"]),
        "replacement_coins_at_escape_risk": p["cost"] * int(baseline["escaped"]),
        "production_next_refresh": int(due),
        "next_production_actions": max(0, production * 24 - step),
        "care_conversion_actions": max(0, care_day * 24 - step),
        "care_conversion_before_terminal": int(care_bankable),
        "care_bonus_with_collection": care_units,
        "care_bonus_without_collection": int(care_units and no_collection_room > 0),
        "care_bonus_current_quote_value": care_units * quote,
        "held_units": tile["yield_units"],
        "banked_care": tile["pending_care_bonus"],
        "care_bank_room": room,
        "next_refresh_units_without_feed": baseline["units"],
        "next_refresh_units_with_feed": fed["units"],
        "next_refresh_units_saved_by_feed": fed["units"] - baseline["units"],
        "bonus_lost_on_unfed_production": tile["pending_care_bonus"]
        * int(due and not tile["fed_today"]),
        "next_production_overflow_without_collection": max(
            0, tile["yield_units"] + 1 + tile["pending_care_bonus"] - p["max_held"]
        )
        * int(due),
        "manure_available": int(tile["fertilizer_available"]),
        "uncollected_manure_slot_at_refresh": int(tile["fertilizer_available"]),
        "daily_feed_current_buy_cost": purchase_cost(
            "WHEAT", obs["market"]["inventory"]["WHEAT"], 1
        ),
    }


def service_plan(tile: dict, obs: dict, position: tuple[int, int], arm: str) -> dict:
    measures = animal_service(tile, obs, position)
    feed = not tile["fed_today"]
    care = not tile["cared_today"]
    if arm != "routine":
        feed = feed and bool(
            measures["escape_without_feed"] or measures["bonus_lost_on_unfed_production"]
        )
    if arm in ("care", "fertilizer"):
        extra_feed_cost = (
            measures["daily_feed_current_buy_cost"] if not tile["fed_today"] and not feed else 0
        )
        care = bool(
            care
            and measures["care_bonus_current_quote_value"]
            > extra_feed_cost + WORK_VALUE * (1 + int(extra_feed_cost > 0))
        )
        feed |= care and not tile["fed_today"]
    return {"feed": bool(feed), "care": bool(care), "measures": measures}


@lru_cache(maxsize=8192)
def _plant_path(tile_json: str, start: int, delay: int, delivery: int, fertilize: bool) -> tuple:
    """Isolated engine rollout: travel, treat, daily water, fixed collection rule.

    Only one copied public plant is simulated. No simulator seed, weed/shop RNG or
    hidden state is consulted. Actual multi-worker feasibility remains separate.
    """
    tile = json.loads(tile_json)
    farm = {"tiles": [[tile]], "farmer": [0, 0], "hands": []}
    private = {"shed": {}, "seeds": {}, "inventories": [{"FERTILIZER": 1}]}
    units = bankable = work = 0
    first = 719
    for step in range(start, min(719, start + PLANT_HORIZON)):
        day = step // 24
        current = farm["tiles"][0][0]
        if not isinstance(current, dict) or current.get("kind") != "PLANT":
            break
        if step < start + delay:
            action = ["PASS"]
        elif fertilize and step == start + delay:
            action = ["FERTILIZE"]
        elif not current["watered_today"]:
            action = ["WATER"]
        elif ready_units(current, day) > 0 and (
            game.CROPS[current["crop"]]["ongoing"]
            or day - current["planted_day"] >= game.CROPS[current["crop"]]["max_yield_day"]
            or 719 - step <= 24
        ):
            action = ["HARVEST"]
        else:
            action = ["PASS"]
        before = private["inventories"][0].get(tile["crop"], 0)
        game._apply_unit_action(farm, private, 0, action, 10, day, 24, 100)
        gained = private["inventories"][0].get(tile["crop"], 0) - before
        work += int(action[0] != "PASS")
        units += gained
        if gained:
            first = min(first, step)
            bankable += gained * int(step + delivery + 1 <= 718)
        game._decay_plants(farm, step)
        if step % 24 == 23:
            game._daily_refresh_plants(farm, day, 24)
    return units, bankable, work, first


def fertilizer_value(obs: dict, position: tuple[int, int], tile: dict, delay: int = 0) -> dict:
    if delay < 0:
        raise ValueError("Negative treatment travel")
    encoded = json.dumps(tile, sort_keys=True)
    delivery = min(distance(position, s) for s in SHED)
    plain = _plant_path(encoded, obs["step"], delay, delivery, False)
    treated = _plant_path(encoded, obs["step"], delay, delivery, True)
    item = tile["crop"]
    inventory = obs["market"]["inventory"][item]
    gain = sale_revenue(item, inventory, treated[1]) - sale_revenue(item, inventory, plain[1])
    manure_sale = game.market_price("FERTILIZER", obs["market"]["inventory"]["FERTILIZER"])
    extra_work = treated[2] - plain[2]
    return {
        "baseline_harvest_units": plain[0],
        "treated_harvest_units": treated[0],
        "bankable_extra_units": treated[1] - plain[1],
        "current_quote_revenue_gain": gain,
        "fertilizer_sale_opportunity": manure_sale,
        "extra_scenario_work": extra_work,
        "net_scenario_value": gain - manure_sale - WORK_VALUE * extra_work,
        "first_harvest_action_gain": plain[3] - treated[3],
    }


def ingredient_route(obs: dict, position: tuple[int, int], item: str) -> int | None:
    farm, private = obs["farms"][obs["player"]], obs["private"]
    routes = []
    for index, unit in enumerate([farm["farmer"], *farm["hands"]]):
        if private["inventories"][index].get(item, 0) > 0:
            routes.append(distance(unit, position))
        if private["shed"].get(item, 0) > 0:
            routes.append(min(distance(unit, s) + 1 + distance(s, position) for s in SHED))
    return min(routes) if routes else None


def livestock_features(observation: dict) -> FeatureVector:
    obs = project_observation(observation)
    f = FeatureVector()
    own = obs["player"]
    for side, player in (("own", own), ("opponent", 1 - own)):
        farm = obs["farms"][player]
        entries = located(farm)
        for animal in sorted(game.ANIMALS):
            group = [(x, y, t) for x, y, t in entries if t.get("animal") == animal]
            # One template makes absence explicit without changing the schema.
            template = animal_service(game._new_animal(animal, obs["day"]), obs, (4, 4))
            rows = [animal_service(t, obs, (x, y)) for x, y, t in group]
            for name in template:
                values = [row[name] for row in rows]
                value = min(values, default=719) if name.endswith("_actions") else sum(values)
                f.add(f"livestock.{side}.{animal}.{name}", value, "livestock_production_timing")
            workers = [farm["farmer"], *farm["hands"]]
            travel = [min(distance(p, (x, y)) for p in workers) for x, y, _ in group]
            for name, value in {
                "worker_route_sum": sum(travel),
                "worker_route_max": max(travel, default=0),
                "feed_route_deadline_failures": sum(
                    dist + 1 > 24 - obs["hour"] and not tile["fed_today"]
                    for dist, (_, _, tile) in zip(travel, group, strict=True)
                ),
            }.items():
                f.add(f"livestock.{side}.{animal}.{name}", value, "livestock_service_routing")

    farm, private = obs["farms"][own], obs["private"]
    totals = product_totals(private)
    animals = [(x, y, t) for x, y, t in located(farm) if t.get("animal")]
    feed_due = sum(not t["fed_today"] for _, _, t in animals)
    emergency = sum(not t["fed_today"] and t["consecutive_unfed"] >= 1 for _, _, t in animals)
    feed_routes = [ingredient_route(obs, (x, y), "WHEAT") for x, y, _ in animals]
    for name, value in {
        "wheat_total": totals["WHEAT"],
        "wheat_in_shed": private["shed"].get("WHEAT", 0),
        "wheat_carried": totals["WHEAT"] - private["shed"].get("WHEAT", 0),
        "feed_due": feed_due,
        "escape_emergencies": emergency,
        "one_day_feed_deficit": max(0, feed_due - totals["WHEAT"]),
        "two_day_feed_deficit": max(0, feed_due + len(animals) - totals["WHEAT"]),
        "feed_covered_days": totals["WHEAT"] / max(1, len(animals)),
        "one_day_feed_buy_cost": purchase_cost(
            "WHEAT", obs["market"]["inventory"]["WHEAT"], max(0, feed_due - totals["WHEAT"])
        ),
        "feed_route_unavailable": sum(route is None for route in feed_routes),
        "feed_route_late": sum(
            route is not None and route + 1 > 24 - obs["hour"] for route in feed_routes
        ),
        "manure_total": totals["FERTILIZER"],
        "manure_in_shed": private["shed"].get("FERTILIZER", 0),
        "manure_collectable": sum(t["fertilizer_available"] for _, _, t in animals),
        "animal_stock_unplaced": sum(
            inv.get(a, 0)
            for inv in [private["shed"], *private["inventories"]]
            for a in game.ANIMALS
        ),
        "product_stock_used": sum(totals.values()),
        "cash_buying_supported": 1,
        "prior_cash_bound_features_supported": 0,
    }.items():
        f.add("livestock.resources." + name, value, "feed_inventory_and_capital")

    for crop in sorted(game.CROPS):
        group = [(x, y, t) for x, y, t in located(farm) if t.get("crop") == crop]
        rows = [fertilizer_value(obs, (x, y), t) for x, y, t in group]
        names = (
            "baseline_harvest_units",
            "treated_harvest_units",
            "bankable_extra_units",
            "current_quote_revenue_gain",
            "fertilizer_sale_opportunity",
            "extra_scenario_work",
            "net_scenario_value",
            "first_harvest_action_gain",
        )
        for name in names:
            f.add(
                f"livestock.fertilizer.{crop}.{name}",
                sum(row[name] for row in rows),
                "fertilizer_counterfactual_value",
            )
        for name, value in {
            "present": len(group),
            "positive_value_plants": sum(r["net_scenario_value"] > 0 for r in rows),
            "best_net_scenario_value": max((r["net_scenario_value"] for r in rows), default=0),
            "ingredient_reachable": sum(
                ingredient_route(obs, (x, y), "FERTILIZER") is not None for x, y, _ in group
            ),
        }.items():
            f.add(f"livestock.fertilizer.{crop}.{name}", value, "fertilizer_counterfactual_value")
    return f
