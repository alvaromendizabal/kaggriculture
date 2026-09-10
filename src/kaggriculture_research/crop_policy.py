"""Deterministic research scaffold for four explicit action-feature interventions.

Conditional crop values assume daily irrigation, no fertilizer, a single harvest,
current prices and no opponent trade. They are scenarios, not learned forecasts.
The common candidate generator, reservation rules and legal-action filter remain
fixed across variants. This is a policy-component ablation, not model selection.
"""

import copy
import math
from dataclasses import asdict, dataclass
from typing import Any

from kaggriculture_research.environment import game
from kaggriculture_research.features import PUBLIC_FIELDS, sale_revenue

VARIANTS = ("full", "no_crop_value", "no_water_urgency", "no_labor", "no_terminal")
SHED = ((4, 4), (4, 5), (5, 4), (5, 5))
FEATURES = {
    "crop_value": ["conditional_units", "conditional_net_coins", "net_coins_per_work_action"],
    "water_urgency": ["dies_next_refresh", "water_bonus_units", "refresh_slack"],
    "labor": ["travel_actions", "workload_actions", "worker_capacity", "next_hire_cost"],
    "terminal": ["decision_slack", "can_bank_crop", "last_day_carry_value"],
}


@dataclass(frozen=True)
class CropScenario:
    units: int
    harvest_age: int
    work_actions: int
    net_coins: float
    bankable: bool


def crop_scenario(crop: str, inventory: int, remaining: int, hour: int) -> CropScenario:
    """One new plant, all daily water, harvest once and allow two delivery actions.

    Plant now; harvest at the earliest hour of its chosen day. The two-action
    delivery allowance is a simplifying scenario, not a route guarantee. The
    scheduler separately checks actual travel feasibility for terminal harvests.
    """
    params = game.CROPS[crop]
    latest_age = max(-1, (remaining - 4 + hour) // 24)
    if params["ongoing"]:
        possible = [
            params["first_yield_day"] + k * params["interval"] for k in range(params["max_yield"])
        ]
        feasible = [age for age in possible if age <= latest_age]
        age = feasible[-1] if feasible else possible[0]
        units = len(feasible)
    else:
        age = min(params["max_yield_day"], latest_age)
        window = (params["max_yield_day"] + 1) // 2
        units = min(params["max_yield"], 1 + max(0, age - window + 1))
        if age < params["first_yield_day"]:
            units = 0
    bankable = units > 0 and 24 * age - hour + 4 <= remaining
    work = max(1, age + 1) + 4  # daily water, plant, harvest, two delivery actions
    net = sale_revenue(crop, inventory, units) - params["seed"] if bankable else -params["seed"]
    return CropScenario(units, age, work, net, bankable)


def distance(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def move_toward(position, target) -> list[str]:
    if position[0] != target[0]:
        return ["EAST" if position[0] < target[0] else "WEST"]
    if position[1] != target[1]:
        return ["SOUTH" if position[1] < target[1] else "NORTH"]
    return ["PASS"]


def water_features(tile: dict, day: int, hour: int) -> dict[str, float]:
    params = game.CROPS[tile["crop"]]
    age = day - tile["planted_day"]
    bonus = 0
    if not tile["watered_today"] and not params["ongoing"]:
        if (params["max_yield_day"] + 1) // 2 <= age <= params["max_yield_day"]:
            bonus = min(
                params["max_yield"] - tile["yield_units"],
                2 if tile["fertilized_until_day"] >= day else 1,
            )
    return {
        "dies_next_refresh": float(
            not tile["watered_today"] and tile["consecutive_unwatered"] >= 1
        ),
        "water_bonus_units": float(bonus),
        "refresh_slack": float(24 - hour),
    }


@dataclass(frozen=True)
class Task:
    target: tuple[int, int]
    action: tuple
    score: float


class CropPolicy:
    def __init__(self, variant: str = "full", max_hands: int = 3, fixed_crop: str | None = None):
        if variant not in VARIANTS:
            raise ValueError(f"Unknown variant: {variant}")
        if not 0 <= max_hands <= 3:
            raise ValueError("This research protocol bounds hired hands at three")
        self.variant = variant
        self.max_hands = max_hands
        self.fixed_crop = fixed_crop
        self.last_diagnostics: dict[str, Any] = {}

    def enabled(self, family: str) -> bool:
        return self.variant != "no_" + family

    def __call__(self, observation: dict[str, Any]) -> dict[str, Any]:
        obs = {k: copy.deepcopy(observation[k]) for k in PUBLIC_FIELDS}
        farm, private = obs["farms"][obs["player"]], obs["private"]
        day, hour, remaining = obs["day"], obs["hour"], 719 - obs["step"]
        prices = obs["market"]["prices"]
        scenarios = {
            crop: crop_scenario(
                crop,
                obs["market"]["inventory"][crop],
                remaining if self.enabled("terminal") else 719,
                hour,
            )
            for crop in sorted(game.CROPS)
            if self.fixed_crop is None or crop == self.fixed_crop
        }
        crop_scores = {
            c: (max(0.0, s.net_coins / s.work_actions / 10) if self.enabled("crop_value") else 1.0)
            for c, s in scenarios.items()
            if not self.enabled("terminal") or (s.bankable and s.net_coins > 0)
        }
        best_crop = min(crop_scores, key=lambda c: (-crop_scores[c], c)) if crop_scores else None
        tasks, irrigation = [], []
        for y, row in enumerate(farm["tiles"]):
            for x, tile in enumerate(row):
                if tile is None and best_crop:
                    # Planting needs a subsequent action for same-day irrigation.
                    if hour < 23:
                        tasks.append(Task((x, y), ("PLANT", best_crop), crop_scores[best_crop]))
                elif isinstance(tile, dict) and tile["kind"] == "WEED" and best_crop:
                    tasks.append(Task((x, y), ("DIG",), crop_scores[best_crop] / 2))
                elif isinstance(tile, dict) and tile["kind"] == "PLANT":
                    if not tile["watered_today"]:
                        wf = water_features(tile, day, hour)
                        priority = 3.0
                        irrigation.append({"tile": [x, y], **water_features(tile, day, hour)})
                        if self.enabled("water_urgency"):
                            priority += (
                                30 * wf["dies_next_refresh"] / math.sqrt(wf["refresh_slack"])
                                + 10 * wf["water_bonus_units"]
                                + 8 / wf["refresh_slack"]
                            )
                        tasks.append(Task((x, y), ("WATER",), priority))
                    params = game.CROPS[tile["crop"]]
                    age = day - tile["planted_day"]
                    ready = age >= params["first_yield_day"] and tile["yield_units"] > 0
                    planned = age >= (
                        params["first_yield_day"] + (params["max_yield"] - 1) * params["interval"]
                        if params["ongoing"]
                        else params["max_yield_day"]
                    )
                    terminal = self.enabled("terminal") and remaining <= 24
                    if ready and (planned or terminal):
                        tasks.append(Task((x, y), ("HARVEST",), 6.0 + (10 if terminal else 0)))

        workload = sum(3 if t.action[0] in ("PLANT", "DIG") else 2 for t in tasks)
        capacity = (1 + len(farm["hands"])) * max(0, 23 - hour)
        reserved = set()
        actions, selected = [], []
        noops = 0
        # Sequential shadow updates exactly follow own-farm unit order; no hidden state.
        positions = [farm["farmer"], *farm["hands"]]
        for idx, position in enumerate(positions):
            options = []
            for task in tasks:
                if task.target in reserved:
                    continue
                dist = distance(position, task.target)
                op = task.action[0]
                if op == "PLANT" and (
                    private["seeds"].get(task.action[1], 0) <= 0 or dist + 2 > 24 - hour
                ):
                    continue
                if op == "WATER" and dist + 1 > 24 - hour:
                    continue
                if self.enabled("terminal") and op == "HARVEST":
                    delivery = min(distance(task.target, s) for s in SHED)
                    if dist + 1 + delivery + 1 > remaining and remaining <= 24 - hour:
                        continue
                score = task.score / (1 + dist) if self.enabled("labor") else task.score
                options.append((score, task))
            inventory = private["inventories"][idx]
            carry = sum(prices.get(c, 0) * n for c, n in inventory.items())
            if carry > 0:
                target = min(SHED, key=lambda s: (distance(position, s), s))
                dist = distance(position, target)
                if dist + 1 <= remaining:
                    priority = 1.0
                    if self.enabled("terminal") and remaining <= 24 - hour:
                        priority += 100 + carry / max(1, remaining - dist)
                    options.append(
                        (
                            priority / (1 + dist) if self.enabled("labor") else priority,
                            Task(target, ("DROP",), priority),
                        )
                    )
            if options:
                _, task = min(options, key=lambda pair: (-pair[0], pair[1].target, pair[1].action))
                # Deposits by different units do not contend for a tile operation.
                if task.action[0] != "DROP":
                    reserved.add(task.target)
                action = (
                    list(task.action)
                    if distance(position, task.target) == 0
                    else move_toward(position, task.target)
                )
                selected.append(
                    {
                        "unit": idx,
                        "target": task.target,
                        "intent": task.action[0],
                        "travel_actions": distance(position, task.target),
                    }
                )
            else:
                action = ["PASS"]
            before = (copy.deepcopy(farm), copy.deepcopy(private))
            game._apply_unit_action(farm, private, idx, action, 10, day, 24, 100)
            if action[0] != "PASS" and before == (farm, private):
                noops += 1
            actions.append(action)

        # Forecast deposits only from the legal own-farm shadow update above.
        # Current carried stock is otherwise not sellable.
        market = [
            ["SELL", c, n]
            for c, n in sorted(private["shed"].items())
            if c in game.PRODUCTS and n > 0
        ]
        cash = farm["money"]  # Do not rely on hypothetical sale proceeds to afford purchases.
        if best_crop and hour < 22:
            empty = sum(t is None for row in farm["tiles"] for t in row)
            quantity = max(0, min(4, empty) - private["seeds"].get(best_crop, 0))
            quantity = min(quantity, cash // game.CROPS[best_crop]["seed"])
            if quantity:
                market.append(["BUY_SEED", best_crop, quantity])
                cash -= quantity * game.CROPS[best_crop]["seed"]
        hire_cost = game._hire_cost(farm["hires_today"])
        if (
            self.enabled("labor")
            and workload > capacity
            and hour < 18
            and remaining > 6
            and len(farm["hands"]) < self.max_hands
            and cash >= hire_cost
        ):
            market.append(["HIRE"])
        if len(market) > 10:
            raise RuntimeError("Research policy exceeded the official market-order limit")
        self.last_diagnostics = {
            "ineffective_farm_actions": noops,
            "selected_tasks": selected,
            "features": {
                "crop_value": {
                    c: {**asdict(s), "net_coins_per_work_action": s.net_coins / s.work_actions}
                    for c, s in scenarios.items()
                },
                "water_urgency": irrigation,
                "labor": {
                    "workload_actions": workload,
                    "worker_capacity": capacity,
                    "next_hire_cost": hire_cost,
                },
                "terminal": {
                    "decision_slack": remaining,
                    "last_day_carry_value": sum(
                        prices.get(c, 0) * n
                        for inv in private["inventories"]
                        for c, n in inv.items()
                    )
                    if remaining <= 24 - hour
                    else 0,
                },
            },
        }
        return {"farmer": actions[0], "hands": actions[1:], "market": market}
