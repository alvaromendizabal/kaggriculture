"""Registered control and sequential final-day interventions."""

from collections import Counter

from kaggriculture_livestock.features import located
from kaggriculture_livestock.policy import LivestockPolicy
from kaggriculture_terminal.feed_policy import FeedPolicy
from kaggriculture_terminal.routing import liquidation

ARMS = ("baseline", "feed", "joint")


class TerminalPolicy:
    def __init__(self, arm: str = "baseline") -> None:
        if arm not in ARMS:
            raise ValueError("Unknown terminal arm")
        self.arm = arm
        self.base = LivestockPolicy("fertilizer") if arm == "baseline" else FeedPolicy("fertilizer")
        self.last_diagnostics = {}

    def __call__(self, obs: dict) -> dict:
        if self.arm != "joint" or obs["day"] != 29:
            action = self.base(obs)
            self.last_diagnostics = self.base.last_diagnostics
            return action
        if self.base.last_step is not None and (
            self.base.last_step + 1 != obs["step"] or self.base.player != obs["player"]
        ):
            raise ValueError("Terminal policy requires consecutive observations")
        action, diagnostics = liquidation(obs)
        self.base.last_step, self.base.player = obs["step"], obs["player"]
        diagnostics.update(
            {
                "animal_counts": dict(
                    Counter(
                        t["animal"]
                        for _, _, t in located(obs["farms"][obs["player"]])
                        if t.get("animal")
                    )
                ),
                "command_counts": dict(Counter(a[0] for a in [action["farmer"], *action["hands"]])),
            }
        )
        self.last_diagnostics = diagnostics
        return action

    def state_dict(self) -> dict:
        return {"arm": self.arm, "base": self.base.state_dict()}

    @classmethod
    def from_state_dict(cls, state: dict) -> "TerminalPolicy":
        if set(state) != {"arm", "base"}:
            raise ValueError("Unexpected terminal state")
        policy = cls(state["arm"])
        kind = LivestockPolicy if policy.arm == "baseline" else FeedPolicy
        policy.base = kind.from_state_dict(state["base"])
        return policy
