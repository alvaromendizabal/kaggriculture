"""Fixed supply-information ablations; delivery and production logic stay frozen."""

import copy

from kaggriculture_research.cash_history import CashHistory
from kaggriculture_research.environment import game
from kaggriculture_research.market_features import two_stage_value, visible_wave, wave_units
from kaggriculture_research.market_history import MarketHistory
from kaggriculture_research.market_policy import MarketPolicy
from kaggriculture_research.relationship_features import town_consumption

ARMS = ("bank", "visible", "history", "cash")


class SupplyPolicy:
    def __init__(self, arm: str, maximum_hold_actions: int = 4, rival_weight: float = 0.5):
        if arm not in ARMS or maximum_hold_actions != 4 or rival_weight != 0.5:
            raise ValueError("Supply study uses the preregistered arms and frozen holding rule")
        self.arm = arm
        self.maximum_hold_actions = maximum_hold_actions
        self.rival_weight = rival_weight
        self.delivery = MarketPolicy("10")
        self.history, self.cash = MarketHistory(), CashHistory()
        self.first_held: dict[str, int] = {}
        self.last_diagnostics: dict = {}
        self.last_features: dict = {}

    def __call__(self, observation: dict) -> dict:
        obs = observation
        if obs["step"] == 0:
            self.first_held.clear()
        loose = self.history.observe(obs)
        tight = self.cash.observe(obs)
        self.last_features = {"history": loose, "cash": tight}
        base = self.delivery(obs)
        action = copy.deepcopy(base)
        held_changes = supply_activations = 0
        if self.arm != "bank":
            # Base SELL amounts are exactly the available post-farm product stocks.
            stocks = {o[1]: o[2] for o in base["market"] if o[0] == "SELL"}
            rival = visible_wave(obs, 1 - obs["player"])
            bound = self.history.upper if self.arm == "history" else self.cash.upper
            orders = []
            for item in sorted(game.PRODUCTS):
                quantity = stocks.get(item, 0)
                if quantity <= 0:
                    self.first_held.pop(item, None)
                    continue
                first = self.first_held.setdefault(item, obs["step"])
                delay = min(
                    self.maximum_hold_actions - (obs["step"] - first),
                    718 - obs["step"],
                    23 - obs["hour"],
                )
                sell = quantity
                if delay > 0:
                    demand = town_consumption(
                        obs["town"]["unlocked_shops"], item, obs["step"], delay
                    )
                    supply = wave_units(rival, item, delay)
                    if self.arm in ("history", "cash"):
                        supply += bound.get(item, 0)
                        supply_activations += int(bound.get(item, 0) > 0)
                    values = []
                    for amount in range(quantity + 1):
                        quiet, stress = two_stage_value(
                            item, obs["market"]["inventory"][item], quantity, amount, demand, supply
                        )
                        values.append(
                            ((1 - self.rival_weight) * quiet + self.rival_weight * stress, amount)
                        )
                    _, sell = max(values)
                held_changes += int(sell != quantity)
                if sell > 0:
                    orders.append(["SELL", item, sell])
                if sell == quantity:
                    self.first_held.pop(item, None)
            orders.extend(o for o in base["market"] if o[0] != "SELL")
            action["market"] = orders
        self.last_diagnostics = copy.deepcopy(self.delivery.last_diagnostics)
        self.last_diagnostics["interventions"]["market_timing"] = held_changes
        self.last_diagnostics["supply_activations"] = supply_activations
        self.last_diagnostics["cash_extra_sale_units"] = sum(
            self.cash.metadata["added_sales"].values()
        )
        self.history.record_action(action)
        self.cash.record_action(action)
        return action

    def state_dict(self) -> dict:
        """Restart state; reference crop/relationship policies contain no learned state."""
        return {
            "arm": self.arm,
            "history": self.history.to_json(),
            "cash": self.cash.to_json(),
            "first_held": self.first_held.copy(),
            "delivery_last_step": self.delivery.last_step,
            "delivery_player": self.delivery.player,
        }

    @classmethod
    def from_state_dict(cls, state: dict) -> "SupplyPolicy":
        policy = cls(state["arm"])
        policy.history = MarketHistory.from_json(state["history"])
        policy.cash = CashHistory.from_json(state["cash"])
        policy.first_held = state["first_held"].copy()
        policy.delivery.last_step, policy.delivery.player = (
            state["delivery_last_step"],
            state["delivery_player"],
        )
        return policy
