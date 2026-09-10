"""Cash-constrained, observation-safe rival supply bounds for sale-only own trading.

The opponent may buy products, seeds, animals or land. We do NOT assume it follows
our reference policy. Product BUY orders by our own agent are outside this version's
contract: they could raise prices and create profitable rival round trips.
"""

import copy
import json
import math
from collections import Counter
from typing import Any

from kaggriculture_research.artifacts import canonical, digest
from kaggriculture_research.environment import game
from kaggriculture_research.features import FeatureVector
from kaggriculture_research.market_features import sale_path
from kaggriculture_research.market_history import BOUNDED_PRODUCTS, MarketHistory

CONTRACT = "public-cash-supply-own-no-product-buys-v1"


def own_sale_quantities(obs: dict, action: dict) -> dict[str, int]:
    """Exact own SELL quantities after legal farm work; product buys are rejected."""
    if any(order and order[0] == "BUY_PRODUCT" for order in action.get("market", [])):
        raise ValueError("Cash supply bounds require no own BUY_PRODUCT orders")
    farm, private = copy.deepcopy((obs["farms"][obs["player"]], obs["private"]))
    units = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
    demand = Counter(a[1] for a in units if len(a) >= 2 and a[0] == "PLANT")
    blocked = {p for p, n in demand.items() if n > private["seeds"].get(p, 0)}
    for index, unit in enumerate(units):
        if len(unit) >= 2 and unit[0] == "PLANT" and unit[1] in blocked:
            unit = ["PASS"]
        game._apply_unit_action(farm, private, index, unit, 10, obs["day"], 24, 100)
    sold = dict.fromkeys(game.PRODUCTS, 0)
    for order in action.get("market", [])[:10]:
        parsed = game._parse_order(order)
        if parsed and parsed["type"] == "SELL" and parsed["item"] in sold:
            item = parsed["item"]
            quantity = min(parsed["remaining"], private["shed"].get(item, 0))
            private["shed"][item] -= quantity
            sold[item] += quantity
    return sold


def visible_minimum_spend(previous: dict, current: dict) -> int:
    """Known rival hiring/land spend; hidden purchases can only add expenditure."""
    rival = 1 - previous["player"]
    old, new = previous["farms"][rival], current["farms"][rival]
    count = len(old["unlocked_quadrants"]) - 1
    added = len(new["unlocked_quadrants"]) - len(old["unlocked_quadrants"])
    if added < 0:
        raise ValueError("Public land ownership decreased")
    spend = sum(game.LAND_PRICES[count : count + added])
    if previous["hour"] != 23:
        hires = new["hires_today"] - old["hires_today"]
        if hires < 0:
            raise ValueError("Hiring counter decreased before the night reset")
        spend += sum(game._hire_cost(old["hires_today"] + k) for k in range(hires))
    return spend


def buyable_revenue_upper(
    item: str, before: int, effective_trade: int, own_sold: int
) -> tuple[float, bool]:
    """Upper bound on rival NET cash from a buyable product, not gross sale units.

    With no own transaction in this product and no reachable price floor, the
    rival's buys/sells telescope along the discrete price curve. If we sell any
    units, short-sale/buyback profit is possible even at zero rival net trade;
    therefore do not subtract our units and pretend the residual identifies cash.
    Fallback: liquidating a full starting shed before our price-depressing sales
    upper-bounds the rival's cash gain. Rival buy-resell cycles cannot exceed that
    bound while our product actions only add supply.
    """
    if item not in ("WHEAT", "FERTILIZER") or not 0 <= own_sold <= 100:
        raise ValueError("Invalid buyable-product cash contract")
    identified = own_sold == 0 and game.market_price(item, before + 100) > 1
    if identified:
        if not -100 <= effective_trade <= 100:
            raise ValueError("Buyable net trade violates the shed conservation bound")
        if effective_trade < 0:
            return -sale_path(item, before + effective_trade, -effective_trade)[0], True
        return sale_path(item, before, effective_trade)[0], True
    return sale_path(item, before, 100)[0], False


class CashHistory:
    """Tighten MarketHistory using public cash; never inspect rival private state."""

    def __init__(self) -> None:
        self.base = MarketHistory()
        self.pending_all: dict[str, int] | None = None
        self.metadata: dict[str, Any] = {}

    @property
    def upper(self) -> dict[str, int]:
        return self.base.upper

    def observe(self, observation: dict) -> FeatureVector:
        previous = self.base.current
        if observation["step"] == 0:
            self.__init__()
            previous = None
        own = self.pending_all
        self.base.observe(observation)
        current = self.base.current
        assert current is not None
        meta: dict[str, Any] = {
            "available": int(previous is not None),
            "cash_delta": 0,
            "minimum_spend": 0,
            "revenue_upper": dict.fromkeys(game.PRODUCTS, 0),
            "buyable_identified": {"WHEAT": False, "FERTILIZER": False},
            "added_sales": dict.fromkeys(BOUNDED_PRODUCTS, 0),
        }
        if previous is not None:
            if own is None:
                raise ValueError("Missing own-action cash bookkeeping")
            row = self.base.rows[-1]
            rival = 1 - current["player"]
            meta["cash_delta"] = (
                current["farms"][rival]["money"] - previous["farms"][rival]["money"]
            )
            meta["minimum_spend"] = visible_minimum_spend(previous, current)
            for item in game.PRODUCTS:
                inventory = previous["market"]["inventory"][item]
                if item in BOUNDED_PRODUCTS:
                    meta["revenue_upper"][item] = sale_path(
                        item, inventory, int(row[item]["sales_upper"])
                    )[0]
                else:
                    upper, identified = buyable_revenue_upper(
                        item, inventory, int(row[item]["trade_net"]), own[item]
                    )
                    meta["revenue_upper"][item] = upper
                    meta["buyable_identified"][item] = identified
            total_upper = sum(meta["revenue_upper"].values())
            required = meta["cash_delta"] + meta["minimum_spend"]
            for item in BOUNDED_PRODUCTS:
                residual = required - (total_upper - meta["revenue_upper"][item])
                ceiling = previous["market"]["prices"][item]
                cash_lower = max(0, math.ceil(residual / ceiling))
                lower = max(int(row[item]["sales_lower"]), cash_lower)
                if lower > row[item]["sales_upper"]:
                    raise ValueError(f"Public cash contradicts the {item} sale interval")
                added = lower - int(row[item]["sales_lower"])
                meta["added_sales"][item] = added
                # Base already applied the night cap. Reconstruct the pre-cap bound
                # from its last row's harvest plus our previous upper is unnecessary:
                # subtracting AFTER a binding cap would be too aggressive. At night
                # use the pre-transition upper retained below instead.
                if previous["hour"] == 23:
                    pre_cap = self._previous_upper[item] + row[item]["harvest_upper"] - lower
                    self.base.upper[item] = min(100, int(pre_cap))
                else:
                    self.base.upper[item] -= added
                row[item]["stock_upper"] = self.base.upper[item]
                row[item]["sales_lower"] = lower
                row[item]["sales_identified"] = int(lower == row[item]["sales_upper"])
                if lower > 0:
                    self.base.last_sale[item] = previous["step"]
        self.pending_all = None
        self.metadata = meta
        self._previous_upper = self.base.upper.copy()
        return self.features()

    def record_action(self, action: dict) -> None:
        if self.base.current is None or self.pending_all is not None:
            raise ValueError("Record one action after a cash-history observation")
        own = own_sale_quantities(self.base.current, action)
        self.base.record_action(action)
        if any(own[p] != self.base.pending_sales[p] for p in BOUNDED_PRODUCTS):
            raise ValueError("Own-sale implementations disagree")
        self.pending_all = own

    def features(self) -> FeatureVector:
        result = FeatureVector()
        for name in ("available", "cash_delta", "minimum_spend"):
            result.add("cash_history." + name, self.metadata[name], "public_cash_accounting")
        for item in BOUNDED_PRODUCTS:
            row = self.base.rows[-1][item] if self.base.rows else {}
            values = {
                "stock_upper": self.base.upper[item],
                "sales_lower": row.get("sales_lower", 0),
                "sales_upper": row.get("sales_upper", 0),
                "additional_sales_identified": self.metadata["added_sales"][item],
                "revenue_upper": self.metadata["revenue_upper"][item],
            }
            for name, value in values.items():
                result.add(f"cash_history.{item}.{name}", value, "cash_constrained_supply")
        for item in ("WHEAT", "FERTILIZER"):
            result.add(
                f"cash_history.{item}.net_cash_identified",
                int(self.metadata["buyable_identified"][item]),
                "buyable_cash_ambiguity",
            )
            result.add(
                f"cash_history.{item}.revenue_upper",
                self.metadata["revenue_upper"][item],
                "buyable_cash_ambiguity",
            )
        return result

    def to_json(self) -> str:
        payload = {
            "contract": CONTRACT,
            "base": self.base.to_json(),
            "pending_all": self.pending_all,
            "metadata": self.metadata,
            "previous_upper": getattr(self, "_previous_upper", dict.fromkeys(BOUNDED_PRODUCTS, 0)),
        }
        return canonical({"payload": payload, "sha256": digest(payload)}).decode()

    @classmethod
    def from_json(cls, serialized: str) -> "CashHistory":
        envelope = json.loads(serialized)
        data = envelope["payload"]
        if digest(data) != envelope["sha256"] or data["contract"] != CONTRACT:
            raise ValueError("Cash-history checksum or contract differs")
        history = cls()
        history.base = MarketHistory.from_json(data["base"])
        history.pending_all, history.metadata = data["pending_all"], data["metadata"]
        history._previous_upper = data["previous_upper"]
        if history.base.current is not None:
            history.features()
        return history
