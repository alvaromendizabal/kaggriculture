"""Fixed feature-policy interventions; not learned forecasting or final optimization."""

import copy

from kaggriculture_research.crop_policy import SHED, distance, move_toward, water_features
from kaggriculture_research.environment import game
from kaggriculture_research.market_features import (
    liquidation_scenarios,
    project_observation,
    two_stage_value,
    visible_wave,
    wave_units,
)
from kaggriculture_research.relationship_features import town_consumption
from kaggriculture_research.relationship_policy import RelationshipPolicy

FACTORS = ("delivery", "market_timing")
ARMS = ("00", "01", "10", "11")


class MarketPolicy:
    def __init__(self, arm: str = "11", maximum_hold_actions: int = 4, rival_weight: float = 0.5):
        if arm not in ARMS or maximum_hold_actions < 1 or not 0 <= rival_weight <= 1:
            raise ValueError("Invalid registered market intervention")
        self.arm = arm
        self.maximum_hold_actions = maximum_hold_actions
        self.rival_weight = rival_weight
        self.reference = RelationshipPolicy("001")
        self.first_held: dict[str, int] = {}
        self.last_step: int | None = None
        self.player: int | None = None
        self.last_diagnostics: dict = {}

    def __call__(self, observation: dict) -> dict:
        obs = project_observation(observation)
        step, player = obs["step"], obs["player"]
        if step == 0:
            self.first_held.clear()
            self.last_step = None
            self.player = None
        if self.last_step is not None and (step != self.last_step + 1 or player != self.player):
            raise ValueError("Policy history must be consecutive and episode/player-local")
        self.last_step, self.player = step, player
        base = self.reference(obs)
        changes = {factor: 0 for factor in FACTORS}
        if self.arm == "00":
            self.last_diagnostics = {"interventions": changes, "delivery_decisions": []}
            return base
        farm, private = copy.deepcopy(obs["farms"][player]), copy.deepcopy(obs["private"])
        original = self.reference.reference.last_diagnostics
        assignments = {task["unit"]: task for task in original["selected_tasks"]}
        opportunity = max(
            (
                max(0, v["net_coins_per_work_action"])
                for v in original["features"]["crop_value"].values()
            ),
            default=0.0,
        )
        rival = visible_wave(obs, 1 - player)
        actions, decisions = [], []
        for index, proposed in enumerate([base["farmer"], *base["hands"]]):
            action = list(proposed)
            position = game._farmer_position(farm, index)
            inventory = private["inventories"][index]
            target = min(SHED, key=lambda tile: (distance(position, tile), tile))
            travel = distance(position, target)
            assignment = assignments.get(index, {"target": position, "intent": "PASS"})
            task_target = assignment["target"]
            detour = travel + 1 + distance(target, task_target) - distance(position, task_target)
            night = 24 - obs["hour"]
            feasible = travel + 1 <= min(night, 719 - step)
            protected = action[0] == "HARVEST"
            tile = farm["tiles"][task_target[1]][task_target[0]]
            if (
                assignment["intent"] == "WATER"
                and isinstance(tile, dict)
                and tile.get("kind") == "PLANT"
            ):
                # Never sacrifice the planned day's survival or bonus watering.
                water = water_features(tile, obs["day"], obs["hour"])
                missed = travel + 1 + distance(target, task_target) + 1 > night
                protected |= missed and bool(
                    water["dies_next_refresh"] or water["water_bonus_units"]
                )
            early = late = 0.0
            for item, quantity in inventory.items():
                if item not in game.PRODUCTS:
                    continue
                quiet, stress = liquidation_scenarios(obs, item, quantity, travel, rival)
                early += (1 - self.rival_weight) * quiet + self.rival_weight * stress
                if step + night <= 718:
                    quiet, stress = liquidation_scenarios(obs, item, quantity, night, rival)
                    late += (1 - self.rival_weight) * quiet + self.rival_weight * stress
            gain = early - late - detour * opportunity
            decisions.append(
                {"unit": index, "gain": gain, "detour": detour, "protected": bool(protected)}
            )
            if self.arm[0] == "1" and inventory and feasible and not protected and gain > 0:
                action = ["DROP"] if travel == 0 else move_toward(position, target)
            if self.arm[0] == "1" and action[0] == "DROP":
                room = max(0, 100 - sum(private["shed"].values()))
                if sum(inventory.values()) > room:
                    available = [item for item, quantity in inventory.items() if quantity > 0]
                    if room and available:
                        item = min(
                            available,
                            key=lambda item: (-obs["market"]["prices"].get(item, 0), item),
                        )
                        action = ["PLACE", item, min(room, inventory[item])]
                    else:
                        action = ["PASS"]
            changes["delivery"] += int(action != proposed)
            game._apply_unit_action(farm, private, index, action, 10, obs["day"], 24, 100)
            actions.append(action)
        orders = []
        for item in sorted(game.PRODUCTS):
            quantity = private["shed"].get(item, 0)
            if quantity <= 0:
                self.first_held.pop(item, None)
                continue
            first = self.first_held.setdefault(item, step)
            delay = min(self.maximum_hold_actions - (step - first), 718 - step, 23 - obs["hour"])
            sell = quantity
            if self.arm[1] == "1" and delay > 0:
                demand = town_consumption(obs["town"]["unlocked_shops"], item, step, delay)
                supply = wave_units(rival, item, delay)
                values = []
                for amount in range(quantity + 1):
                    quiet, stress = two_stage_value(
                        item, obs["market"]["inventory"][item], quantity, amount, demand, supply
                    )
                    values.append(
                        ((1 - self.rival_weight) * quiet + self.rival_weight * stress, amount)
                    )
                _, sell = max(values)  # Equal scenario values prefer earlier banking.
            changes["market_timing"] += int(sell != quantity)
            if sell > 0:
                orders.append(["SELL", item, sell])
            if sell == quantity:
                self.first_held.pop(item, None)
        orders.extend(order for order in base["market"] if order[0] != "SELL")
        if len(orders) > 10:
            raise ValueError("Official market order limit exceeded")
        self.last_diagnostics = {"interventions": changes, "delivery_decisions": decisions}
        return {"farmer": actions[0], "hands": actions[1:], "market": orders}
