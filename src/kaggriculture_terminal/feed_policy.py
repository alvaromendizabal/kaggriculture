"""Explicit Study 5 policy fork: terminal feed gate and feed reserve only.

Layout, acquisition, staffing, harvesting and transport stay common across arms.
Scores are registered engineering constants, not fitted weights or learned values.
"""

import copy
from collections import Counter
from dataclasses import dataclass

from kaggriculture_livestock.features import (
    fertilizer_value,
    located,
    product_totals,
    purchase_cost,
)
from kaggriculture_livestock.features import service_plan as original_service_plan
from kaggriculture_research.crop_policy import SHED, distance, move_toward, water_features
from kaggriculture_research.environment import game
from kaggriculture_research.market_features import project_observation
from kaggriculture_research.relationship_features import ready_units


def service_plan(tile: dict, obs: dict, position: tuple[int, int], arm: str) -> dict:
    plan = original_service_plan(tile, obs, position, arm)
    if obs["day"] == 29:
        plan["feed"] = False
    return plan


ARMS = ("routine", "feed", "care", "fertilizer")
ANIMAL_LAYOUT = {
    (4, 4): "GOOSE",
    (3, 4): "COW",
    (4, 3): "SHEEP",
    (2, 4): "GOOSE",
    (3, 3): "COW",
    (4, 2): "SHEEP",
}
CROP_LAYOUT = {
    (2, 3): "WHEAT",
    (3, 2): "WHEAT",
    (1, 4): "WHEAT",
    (4, 1): "WHEAT",
    (2, 2): "STRAWBERRY",
    (1, 3): "STRAWBERRY",
    (3, 1): "STRAWBERRY",
    (0, 4): "TOMATO",
    (4, 0): "TOMATO",
    (1, 2): "TOMATO",
}


@dataclass(frozen=True)
class Job:
    target: tuple[int, int]
    command: tuple
    priority: float
    today: bool = False


class FeedPolicy:
    def __init__(self, arm: str = "routine") -> None:
        if arm not in ARMS:
            raise ValueError("Unknown livestock research arm")
        self.arm = arm
        self.last_step = None
        self.player = None
        self.last_diagnostics: dict = {}

    def __call__(self, observation: dict) -> dict:
        obs = copy.deepcopy(project_observation(observation))
        if obs["step"] == 0:
            self.last_step = self.player = None
        if self.last_step is not None and (
            obs["step"] != self.last_step + 1 or obs["player"] != self.player
        ):
            raise ValueError("Livestock policy must consume consecutive episode-local observations")
        self.last_step, self.player = obs["step"], obs["player"]
        farm, private = obs["farms"][obs["player"]], obs["private"]
        remaining, night = 719 - obs["step"], 24 - obs["hour"]
        original_animals = [(x, y, t) for x, y, t in located(farm) if t.get("animal")]
        original_plans = [service_plan(t, obs, (x, y), self.arm) for x, y, t in original_animals]
        actions, selections, reserved = [], [], set()
        noops = 0
        for index in range(1 + len(farm["hands"])):
            position = game._farmer_position(farm, index)
            inventory = private["inventories"][index]
            jobs = []
            for target, animal in ANIMAL_LAYOUT.items():
                x, y = target
                tile = farm["tiles"][y][x]
                if tile is None and obs["day"] < 12:
                    jobs.append(Job(target, ("BUILD_" + game.ANIMALS[animal]["structure"],), 150))
                elif isinstance(tile, dict) and tile.get("kind") == "WEED":
                    jobs.append(Job(target, ("DIG",), 150))
                elif isinstance(tile, dict) and "animal" not in tile:
                    if inventory.get(animal, 0) > 0:
                        jobs.append(Job(target, ("PLACE", animal), 180))

            feed_tasks = care_tasks = 0
            for x, y, tile in located(farm):
                target = (x, y)
                if tile.get("animal"):
                    plan = service_plan(tile, obs, target, self.arm)
                    feed_tasks += int(plan["feed"])
                    care_tasks += int(plan["care"])
                    measures = plan["measures"]
                    if plan["feed"] and inventory.get("WHEAT", 0) > 0:
                        jobs.append(
                            Job(
                                target, ("FEED",), 220 + 400 * measures["escape_without_feed"], True
                            )
                        )
                    if plan["care"]:
                        priority = 50.0
                        if self.arm in ("care", "fertilizer"):
                            priority += measures["care_bonus_current_quote_value"] / 10
                        jobs.append(Job(target, ("CARE",), priority, True))
                    if tile["yield_units"] > 0:
                        item = game.ANIMALS[tile["animal"]]["product"]
                        priority = 80 + obs["market"]["prices"][item] * tile["yield_units"] / 10
                        priority += 80 * int(
                            measures["next_production_overflow_without_collection"] > 0
                        )
                        jobs.append(Job(target, ("HARVEST",), priority))
                    if tile["fertilizer_available"]:
                        priority = 45 + obs["market"]["prices"]["FERTILIZER"] / 10
                        jobs.append(Job(target, ("COLLECT_FERTILIZER",), priority))
                elif tile.get("kind") == "PLANT":
                    if not tile["watered_today"]:
                        water = water_features(tile, obs["day"], obs["hour"])
                        jobs.append(
                            Job(
                                target,
                                ("WATER",),
                                90
                                + 250 * water["dies_next_refresh"]
                                + 10 * water["water_bonus_units"],
                                True,
                            )
                        )
                    if ready_units(tile, obs["day"]) > 0:
                        # Ongoing crops are collected between events, exposing treatment gains.
                        p = game.CROPS[tile["crop"]]
                        age = obs["day"] - tile["planted_day"]
                        if p["ongoing"] or age >= p["max_yield_day"] or remaining <= 24:
                            value = tile["yield_units"] * obs["market"]["prices"][tile["crop"]]
                            jobs.append(Job(target, ("HARVEST",), 80 + value / 10))
                    if self.arm == "fertilizer" and inventory.get("FERTILIZER", 0) > 0:
                        value = fertilizer_value(obs, target, tile, distance(position, target))
                        if value["net_scenario_value"] > 0:
                            jobs.append(
                                Job(target, ("FERTILIZE",), 40 + value["net_scenario_value"] / 8)
                            )

            for target, crop in CROP_LAYOUT.items():
                x, y = target
                tile = farm["tiles"][y][x]
                p = game.CROPS[crop]
                if remaining <= p["first_yield_day"] * 24 + 12:
                    continue
                if tile is None and private["seeds"].get(crop, 0) > 0:
                    jobs.append(Job(target, ("PLANT", crop), 30, True))
                elif isinstance(tile, dict) and tile.get("kind") == "WEED":
                    jobs.append(Job(target, ("DIG",), 25))

            shed = min(SHED, key=lambda s: (distance(position, s), s))
            travel = distance(position, shed)
            # Targeted deposits keep useful feed/treatment stock in a worker's hands.
            for item, amount in sorted(inventory.items()):
                reserve = feed_tasks if item == "WHEAT" else 0
                if item == "FERTILIZER" and self.arm == "fertilizer" and remaining > 24:
                    reserve = 1
                quantity = max(0, amount - reserve)
                room = max(0, 100 - sum(private["shed"].values()))
                if item in game.PRODUCTS and quantity and room and travel + 1 <= remaining:
                    value = obs["market"]["prices"][item] * quantity
                    priority = 35 + value / 20 + (1000 if remaining <= 24 else 0)
                    jobs.append(Job(shed, ("PLACE", item, min(room, quantity)), priority))
            if feed_tasks and not inventory.get("WHEAT", 0) and private["shed"].get("WHEAT", 0):
                amount = min(feed_tasks, private["shed"]["WHEAT"])
                jobs.append(Job(shed, ("PICKUP", "WHEAT", amount), 230, True))
            for animal in sorted(game.ANIMALS):
                if private["shed"].get(animal, 0) and not inventory.get(animal, 0):
                    jobs.append(Job(shed, ("PICKUP", animal, 1), 170))
            if (
                self.arm == "fertilizer"
                and not inventory.get("FERTILIZER", 0)
                and private["shed"].get("FERTILIZER", 0)
            ):
                best = max(
                    (
                        fertilizer_value(obs, (x, y), tile, travel + 1 + distance(shed, (x, y)))[
                            "net_scenario_value"
                        ]
                        for x, y, tile in located(farm)
                        if tile.get("kind") == "PLANT"
                    ),
                    default=0,
                )
                if best > 0:
                    jobs.append(Job(shed, ("PICKUP", "FERTILIZER", 1), 40 + best / 8))

            options = []
            for job in jobs:
                travel = distance(position, job.target)
                op = job.command[0]
                if (job.target, op) in reserved and travel:
                    continue
                extra = 2 if op == "PLANT" else 1
                if job.today and travel + extra > night:
                    continue
                if op in ("HARVEST", "COLLECT_FERTILIZER"):
                    deposit = min(distance(job.target, s) for s in SHED)
                    if travel + 1 + deposit + 1 > remaining:
                        continue
                options.append((job.priority / (1 + travel), job))
            if options:
                score, chosen = min(
                    options, key=lambda pair: (-pair[0], pair[1].target, pair[1].command)
                )
                action = (
                    list(chosen.command)
                    if position == list(chosen.target)
                    else move_toward(position, chosen.target)
                )
                if action[0] in game.FARMER_MOVES:
                    reserved.add((chosen.target, chosen.command[0]))
                selections.append(
                    {
                        "unit": index,
                        "target": list(chosen.target),
                        "intent": chosen.command[0],
                        "score": score,
                    }
                )
            else:
                action = ["PASS"]
            before = copy.deepcopy((farm, private))
            game._apply_unit_action(farm, private, index, action, 10, obs["day"], 24, 100)
            noops += int(action[0] != "PASS" and before == (farm, private))
            actions.append(action)

        animals = [t for _, _, t in located(farm) if t.get("animal")]
        active = len(animals)
        stock = product_totals(private)
        reserve_feed = 2 * active if obs["day"] < 29 else 0
        reserve_manure = 0
        if self.arm == "fertilizer":
            reserve_manure = min(
                3,
                sum(
                    fertilizer_value(obs, (x, y), t)["net_scenario_value"] > 0
                    for x, y, t in located(farm)
                    if t.get("kind") == "PLANT"
                ),
            )
        orders = []
        for item in sorted(game.PRODUCTS):
            reserve = (
                reserve_feed if item == "WHEAT" else reserve_manure if item == "FERTILIZER" else 0
            )
            held = private["shed"].get(item, 0)
            amount = max(0, held - max(0, reserve - (stock[item] - held)))
            if obs["day"] == 29 and remaining <= 8:
                amount = held
            if amount:
                orders.append(["SELL", item, amount])
        cash = farm["money"]
        wanted = max(0, reserve_feed - stock["WHEAT"])
        wanted = min(wanted, max(0, 100 - sum(private["shed"].values())))
        while wanted and purchase_cost("WHEAT", obs["market"]["inventory"]["WHEAT"], wanted) > cash:
            wanted -= 1
        if wanted and obs["day"] < 29 and len(orders) < 10:
            orders.append(["BUY_PRODUCT", "WHEAT", wanted])
            cash -= purchase_cost("WHEAT", obs["market"]["inventory"]["WHEAT"], wanted)
        if obs["hour"] < 6 and len(farm["hands"]) < 3 and len(orders) < 10:
            price = game._hire_cost(farm["hires_today"])
            if cash >= price:
                orders.append(["HIRE"])
                cash -= price
        counts = Counter(t["animal"] for t in animals)
        for inv in [private["shed"], *private["inventories"]]:
            counts.update({a: inv.get(a, 0) for a in game.ANIMALS})
        if obs["day"] < 12:
            for animal in ("GOOSE", "COW", "SHEEP"):
                cost = game.ANIMALS[animal]["cost"]
                reserve = 300 + purchase_cost(
                    "WHEAT", obs["market"]["inventory"]["WHEAT"], 2 * active
                )
                if counts[animal] < 2 and cash - cost >= reserve and len(orders) < 10:
                    orders.append(["BUY_ANIMAL", animal, 1])
                    cash -= cost
                    break
        for crop in ("WHEAT", "TOMATO", "STRAWBERRY"):
            targets = sum(
                desired == crop
                and (farm["tiles"][y][x] is None or farm["tiles"][y][x].get("kind") == "WEED")
                for (x, y), desired in CROP_LAYOUT.items()
            )
            wanted = max(0, min(2, targets) - private["seeds"].get(crop, 0))
            price = game.CROPS[crop]["seed"]
            wanted = min(wanted, max(0, int((cash - 100) // price)))
            if (
                wanted
                and remaining > game.CROPS[crop]["first_yield_day"] * 24 + 12
                and len(orders) < 10
            ):
                orders.append(["BUY_SEED", crop, wanted])
                cash -= wanted * price
        self.last_diagnostics = {
            "selected_tasks": selections,
            "ineffective_farm_actions": noops,
            "planned_feed_tiles": sum(p["feed"] for p in original_plans),
            "planned_care_tiles": sum(p["care"] for p in original_plans),
            "animal_counts": dict(Counter(t["animal"] for _, _, t in original_animals)),
            "command_counts": dict(Counter(a[0] for a in actions)),
        }
        return {"farmer": actions[0], "hands": actions[1:], "market": orders}

    def state_dict(self) -> dict:
        return {"arm": self.arm, "last_step": self.last_step, "player": self.player}

    @classmethod
    def from_state_dict(cls, state: dict) -> "FeedPolicy":
        if set(state) != {"arm", "last_step", "player"}:
            raise ValueError("Unexpected livestock policy state")
        policy = cls(state["arm"])
        policy.last_step, policy.player = state["last_step"], state["player"]
        return policy
