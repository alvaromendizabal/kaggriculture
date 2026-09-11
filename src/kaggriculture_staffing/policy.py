"""Two-arm terminal policy that isolates routing from staffing and market logic.

Both arms run the same fertilizer/feed-gated base policy and therefore use the
same hiring and market *rule*. On day 29 only, ``coordinated`` replaces the farm
unit actions with the bounded conflict-aware route assignment from Study 6.
The base market orders are retained so the treatment does not silently change
hiring or liquidation policy while testing farm routing.
"""

from __future__ import annotations

import copy
from collections import Counter

from kaggriculture_livestock.policy import FeedPolicy
from kaggriculture_research.market_features import project_observation
from kaggriculture_staffing.features import staffing_features
from kaggriculture_terminal.routing import liquidation

ARMS = ("sequential", "coordinated")


class StaffingPolicy:
    """Staffing-controlled sequential versus coordinated terminal routing."""

    def __init__(self, arm: str = "sequential") -> None:
        if arm not in ARMS:
            raise ValueError("Unknown staffing arm")
        self.arm = arm
        self.base = FeedPolicy("fertilizer")
        self.last_diagnostics: dict = {}

    def __call__(self, observation: dict) -> dict:
        obs = project_observation(observation)
        before = copy.deepcopy(obs)
        base_action = self.base(obs)
        if obs != before:
            raise ValueError("Base policy mutated the legal observation")

        features = staffing_features(obs)
        coordinated_diagnostics: dict = {}
        farm_action = base_action
        if self.arm == "coordinated" and obs["day"] == 29:
            routed, coordinated_diagnostics = liquidation(obs)
            farm_action = {
                "farmer": routed["farmer"],
                "hands": routed["hands"],
                # Preserve the exact shared hiring/selling rule from the base policy.
                "market": base_action["market"],
            }

        hands = obs["farms"][obs["player"]]["hands"]
        actions = [farm_action["farmer"], *farm_action["hands"]]
        if len(actions) != 1 + len(hands):
            raise ValueError("Farm action count differs from active worker count")
        hire_orders = sum(order[0] == "HIRE" for order in base_action["market"])
        self.last_diagnostics = {
            "arm": self.arm,
            "day": obs["day"],
            "hour": obs["hour"],
            "step": obs["step"],
            "active_workers": 1 + len(hands),
            "hired_hands": len(hands),
            "hire_orders": hire_orders,
            "market_orders": copy.deepcopy(base_action["market"]),
            "command_counts": dict(Counter(action[0] for action in actions)),
            "base_diagnostics": copy.deepcopy(self.base.last_diagnostics),
            "route_diagnostics": copy.deepcopy(coordinated_diagnostics),
            "staffing_features": dict(features.values),
        }
        return farm_action

    def state_dict(self) -> dict:
        return {"arm": self.arm, "base": self.base.state_dict()}

    @classmethod
    def from_state_dict(cls, state: dict) -> "StaffingPolicy":
        if set(state) != {"arm", "base"}:
            raise ValueError("Unexpected staffing state")
        policy = cls(state["arm"])
        policy.base = FeedPolicy.from_state_dict(state["base"])
        return policy
