"""Finite, fixed-schema descriptors computed solely from the current legal observation.

These are research candidates, not selected predictors. No seed, reward, future replay,
opponent private inventory, or hidden simulator object enters this interface.
"""

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from kaggriculture_research.environment import game

PUBLIC_FIELDS = ("player", "step", "day", "hour", "farms", "market", "town", "private")


@dataclass
class FeatureVector:
    values: dict[str, float] = field(default_factory=dict)
    families: dict[str, str] = field(default_factory=dict)

    def add(self, name: str, value: float, family: str) -> None:
        if name in self.values:
            raise ValueError(f"Duplicate feature name: {name}")
        if not math.isfinite(value):
            raise ValueError(f"Non-finite feature: {name}")
        self.values[name] = float(value)
        self.families[name] = family


def sale_revenue(item: str, inventory: int, quantity: int) -> float:
    """Exact immediate single-player sale; assumes no concurrent opponent order.

    This is a conditional scenario, not a prediction of the opponent or future prices.
    The official floor does not add market inventory on sales priced at one coin.
    """
    if quantity < 0:
        raise ValueError("quantity must be nonnegative")
    total = 0.0
    for _ in range(quantity):
        price = game.market_price(item, inventory)
        total += price
        inventory += int(price > 1)
    return total


def observe_features(observation: dict[str, Any]) -> FeatureVector:
    # Explicitly project the actual callback observation. Extra replay metadata is ignored.
    obs = {k: observation[k] for k in PUBLIC_FIELDS}
    player = obs["player"]
    if player not in (0, 1) or len(obs["farms"]) != 2:
        raise ValueError("Expected a two-player observation")
    f = FeatureVector()
    step, day, hour = int(obs["step"]), int(obs["day"]), int(obs["hour"])
    # Official 720 states include state 0; the pinned engine executes 719 decisions.
    for name, value in {
        "day": day,
        "hour": hour,
        "decisions_remaining": max(0, 719 - step),
        "hours_until_refresh": 24 - hour,
        "season_fraction": step / 719,
    }.items():
        f.add("time." + name, value, "horizon")

    own = obs["farms"][player]
    other = obs["farms"][1 - player]
    f.add("relative.cash_lead", own["money"] - other["money"], "relative_state")
    f.add("relative.worker_lead", len(own["hands"]) - len(other["hands"]), "relative_state")
    f.add(
        "relative.land_lead",
        len(own["unlocked_quadrants"]) - len(other["unlocked_quadrants"]),
        "relative_state",
    )

    private = obs["private"]
    shed = private["shed"]
    carried = Counter()
    for inventory in private["inventories"]:
        carried.update(inventory)
    f.add("logistics.shed_used", sum(shed.values()), "logistics")
    f.add("logistics.shed_free", max(0, 100 - sum(shed.values())), "logistics")
    f.add("logistics.carried_total", sum(carried.values()), "logistics")
    f.add(
        "logistics.refresh_overflow",
        max(0, sum(shed.values()) + sum(carried.values()) - 100),
        "logistics",
    )

    shops = Counter(obs["town"]["unlocked_shops"])
    for shop in sorted(game.SHOPS):
        f.add(f"demand.{shop}.instances", shops[shop], "town_demand")
    for item in game.PRODUCTS:
        inventory = obs["market"]["inventory"][item]
        price = obs["market"]["prices"][item]
        p = game.MARKET_PARAMS[item]
        # This extractor supports only the official default market, checked by the protocol.
        if price != game.market_price(item, inventory):
            raise ValueError("Observation prices differ from the pinned default price curves")
        shop_demand = sum(
            n * (2 if len(game.SHOPS[s]) == 1 else 1)
            for s, n in shops.items()
            if item in game.SHOPS[s]
        )
        values = {
            "price": price,
            "normalized_price": price / p["base"],
            "normalized_supply": (inventory - p["I0"]) / p["T"],
            "one_unit_price_impact": price - game.market_price(item, inventory + 1),
            "sell_5_revenue": sale_revenue(item, inventory, 5),
            "sell_20_revenue": sale_revenue(item, inventory, 20),
        }
        for name, value in values.items():
            f.add(f"market.{item}.{name}", value, "market_curves")
        f.add(
            f"demand.{item}.current_daily_units",
            6 * shop_demand + int(item != "FERTILIZER"),
            "town_demand",
        )
        f.add(f"inventory.{item}.shed", shed.get(item, 0), "logistics")
        f.add(f"inventory.{item}.carried", carried.get(item, 0), "logistics")
        f.add(
            f"inventory.{item}.immediate_sale_value",
            sale_revenue(item, inventory, int(shed.get(item, 0))),
            "market_curves",
        )
    for crop in game.CROPS:
        f.add(f"inventory.{crop}.seeds", private["seeds"].get(crop, 0), "logistics")
    for animal in game.ANIMALS:
        f.add(
            f"inventory.{animal}.unplaced",
            shed.get(animal, 0) + carried.get(animal, 0),
            "logistics",
        )

    for side, farm in (("own", own), ("opponent", other)):
        tiles = [(x, y, t) for y, row in enumerate(farm["tiles"]) for x, t in enumerate(row)]
        if len(farm["tiles"]) != 10 or any(len(row) != 10 for row in farm["tiles"]):
            raise ValueError("Feature contract expects official 10x10 boards")
        plants = [t for _, _, t in tiles if isinstance(t, dict) and t.get("kind") == "PLANT"]
        animals = [t for _, _, t in tiles if isinstance(t, dict) and t.get("animal")]
        fx, fy = farm["farmer"]
        summary = {
            "cash": farm["money"],
            "workers": 1 + len(farm["hands"]),
            "empty_tiles": sum(t is None for _, _, t in tiles),
            "weed_tiles": sum(isinstance(t, dict) and t.get("kind") == "WEED" for _, _, t in tiles),
            "unlocked_tiles": sum(t != "LOCKED" for _, _, t in tiles),
            "next_hire_cost": game._hire_cost(farm["hires_today"]),
            "worker_turns_today": (1 + len(farm["hands"])) * (24 - hour),
            "water_actions_due": sum(not t["watered_today"] for t in plants),
            "feed_actions_due": sum(not t["fed_today"] for t in animals),
            "shed_distance": min(
                abs(fx - x) + abs(fy - y) for x, y in ((4, 4), (4, 5), (5, 4), (5, 5))
            ),
        }
        for name, value in summary.items():
            f.add(f"{side}.{name}", value, "labor_land")
        for crop, params in game.CROPS.items():
            group = [t for t in plants if t["crop"] == crop]
            ages = [day - t["planted_day"] for t in group]
            values = {
                "count": len(group),
                "mean_age": sum(ages) / len(ages) if ages else 0,
                "harvestable_units": sum(
                    t["yield_units"]
                    for t, age in zip(group, ages, strict=True)
                    if age >= params["first_yield_day"]
                ),
                "water_due": sum(not t["watered_today"] for t in group),
                "death_risk_today": sum(
                    not t["watered_today"] and t["consecutive_unwatered"] >= 1 for t in group
                ),
                "bonus_water_opportunities": sum(
                    not params["ongoing"]
                    and not t["watered_today"]
                    and (params["max_yield_day"] + 1) // 2 <= age <= params["max_yield_day"]
                    and t["yield_units"] < params["max_yield"]
                    for t, age in zip(group, ages, strict=True)
                ),
                "fertilized_count": sum(t["fertilized_until_day"] >= day for t in group),
            }
            for name, value in values.items():
                f.add(f"{side}.crop.{crop}.{name}", value, "crop_state")
        for animal in game.ANIMALS:
            group = [t for t in animals if t["animal"] == animal]
            values = {
                "count": len(group),
                "yield_units": sum(t["yield_units"] for t in group),
                "feed_due": sum(not t["fed_today"] for t in group),
                "escape_risk_today": sum(
                    not t["fed_today"] and t["consecutive_unfed"] >= 1 for t in group
                ),
                "fertilizer_available": sum(t["fertilizer_available"] for t in group),
                "care_bonus_banked": sum(t.get("pending_care_bonus", 0) for t in group),
            }
            for name, value in values.items():
                f.add(f"{side}.animal.{animal}.{name}", value, "animal_state")
    return f
