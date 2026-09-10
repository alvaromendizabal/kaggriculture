"""Three transparent interventions around the frozen first-study scheduler.

This is NOT final policy optimization. The all-off arm returns the frozen policy
unchanged. The 2x2x2 design measures conditional component and interaction effects.
Early collection is deliberately local (a worker already on a capped mature crop),
not a claim to solve global harvest scheduling. Full route planning remains open.
"""

import copy
from itertools import product
from typing import Any

from kaggriculture_research.crop_policy import SHED, CropPolicy, distance, move_toward
from kaggriculture_research.environment import game
from kaggriculture_research.relationship_features import (
    capped_ready,
    cash_reserve,
    inventory_pressure,
    shed_distance,
)

FACTORS = ("capacity", "capital", "maturity")
ARMS = tuple("".join(map(str, bits)) for bits in product((0, 1), repeat=3))


class RelationshipPolicy:
    def __init__(self, arm: str = "111") -> None:
        if arm not in ARMS:
            raise ValueError(f"Unknown factorial arm: {arm}")
        self.arm = arm
        self.enabled = dict(zip(FACTORS, map(bool, map(int, arm)), strict=True))
        self.reference = CropPolicy("full", 3)
        self.last_diagnostics: dict[str, Any] = {}

    def __call__(self, observation: dict) -> dict:
        base = self.reference(observation)
        if self.arm == "000":
            self.last_diagnostics = {**self.reference.last_diagnostics, "interventions": {}}
            return base
        obs = observation
        farm = copy.deepcopy(obs["farms"][obs["player"]])
        private = copy.deepcopy(obs["private"])
        pressure = inventory_pressure(obs)
        reserve = cash_reserve(obs)
        remaining = 719 - obs["step"]
        actions, interventions = [], {f: 0 for f in FACTORS}
        noops = 0
        for i, proposed in enumerate([base["farmer"], *base["hands"]]):
            position = game._farmer_position(farm, i)
            inventory = private["inventories"][i]
            tile = farm["tiles"][position[1]][position[0]]
            action = list(proposed)
            # Collect at the yield cap; no more yield can be gained by waiting.
            if self.enabled["maturity"] and capped_ready(tile, obs["day"]):
                if 2 + shed_distance(position) <= remaining or remaining > 24 - obs["hour"]:
                    action = ["HARVEST"]
                    interventions["maturity"] += int(action != proposed)
            if self.enabled["capacity"]:
                # Ready-wave scenario is deliberately conservative: not all standing
                # units necessarily reach storage today. Test the opportunity cost.
                risk = pressure["ready_wave_overflow_after_sell_all"] > 0
                target = min(SHED, key=lambda s: (distance(position, s), s))
                feasible = distance(position, target) + 1 <= min(remaining, 24 - obs["hour"])
                if inventory and risk and feasible:
                    action = (
                        ["DROP"]
                        if position == list(target) or tuple(position) == target
                        else move_toward(position, target)
                    )
                if action[0] == "DROP" and sum(inventory.values()) > max(
                    0, 100 - sum(private["shed"].values())
                ):
                    room = max(0, 100 - sum(private["shed"].values()))
                    products = [c for c, n in inventory.items() if n > 0 and c in game.PRODUCTS]
                    if room and products:
                        item = min(products, key=lambda c: (-obs["market"]["prices"][c], c))
                        action = ["PLACE", item, min(room, inventory[item])]
                    else:
                        action = ["PASS"]  # Sell present stock, deposit on a later turn.
                interventions["capacity"] += int(action != proposed)
            before = (copy.deepcopy(farm), copy.deepcopy(private))
            game._apply_unit_action(farm, private, i, action, 10, obs["day"], 24, 100)
            if action[0] != "PASS" and before == (farm, private):
                noops += 1
            actions.append(action)
        # Any redirected deposit/harvest changes what can actually be sold now.
        orders = [
            ["SELL", c, n]
            for c, n in sorted(private["shed"].items())
            if c in game.PRODUCTS and n > 0
        ]
        cash = farm["money"]
        for order in base["market"]:
            if order[0] == "BUY_SEED":
                _, crop, n = order
                if self.enabled["capital"]:
                    n = min(
                        n, int(max(0, cash - reserve["labor_reserve"]) // game.CROPS[crop]["seed"])
                    )
                    interventions["capital"] += int(n != order[2])
                if n:
                    orders.append(["BUY_SEED", crop, n])
                    cash -= n * game.CROPS[crop]["seed"]
            elif order[0] == "HIRE":
                orders.append(order)
        # If seed reservation made a previously unaffordable hire possible, use
        # the same frozen workload/capacity eligibility and the same three-hand cap.
        labor = self.reference.last_diagnostics["features"]["labor"]
        if self.enabled["capital"] and not any(o[0] == "HIRE" for o in orders):
            if (
                labor["workload_actions"] > labor["worker_capacity"]
                and obs["hour"] < 18
                and remaining > 6
                and len(farm["hands"]) < 3
                and cash >= labor["next_hire_cost"]
            ):
                orders.append(["HIRE"])
                interventions["capital"] += 1
        if len(orders) > 10:
            raise ValueError("Market order limit exceeded")
        self.last_diagnostics = {
            "ineffective_farm_actions": noops,
            "interventions": interventions,
            "storage": pressure,
            "capital": reserve,
        }
        return {"farmer": actions[0], "hands": actions[1:], "market": orders}
