"""Causal public-market history and set-valued rival supply, not a fitted belief.

Gross-sale/stock bounds cover the seven products the opponent cannot buy. Wheat
and fertilizer retain public net-flow histories but have explicit unsupported
stock masks. No opponent action, private stock, seed or future observation is an
input. The contract is the pinned default game, from callback zero, <=3 hands.
"""

import copy
import json
import math
from collections import Counter
from typing import Any

from kaggriculture_research.artifacts import canonical, digest
from kaggriculture_research.environment import game
from kaggriculture_research.features import FeatureVector
from kaggriculture_research.market_features import project_observation
from kaggriculture_research.relationship_features import town_consumption

WINDOWS = (4, 12, 24)
BOUNDED_PRODUCTS = tuple(p for p in game.PRODUCTS if p not in ("WHEAT", "FERTILIZER"))
TILE_FIELDS = (
    "kind",
    "crop",
    "planted_day",
    "watered_today",
    "consecutive_unwatered",
    "yield_units",
    "max_lifespan_step",
    "fertilized_until_day",
    "animal",
    "placed_day",
    "fed_today",
    "cared_today",
    "consecutive_unfed",
    "fertilizer_available",
    "pending_care_bonus",
)
FARM_FIELDS = ("money", "farmer", "hands", "unlocked_quadrants", "hires_today")
CONTRACT = "default-719-callbacks-100-shed-3-hands-public-history-v1"


def _snapshot(observation: dict[str, Any]) -> dict[str, Any]:
    obs = project_observation(observation)
    step = obs["step"]
    if type(step) is not int or not 0 <= step <= 718:
        raise ValueError("Expected a decision callback from 0 through 718")
    if (obs["day"], obs["hour"]) != divmod(step, 24):
        raise ValueError("History calendar differs from the default 24-turn day")
    farms = []
    for farm in obs["farms"]:
        if len(farm["tiles"]) != 10 or any(len(row) != 10 for row in farm["tiles"]):
            raise ValueError("Expected default 10x10 public farms")
        projected = {key: copy.deepcopy(farm[key]) for key in FARM_FIELDS}
        projected["tiles"] = [
            [{k: t[k] for k in TILE_FIELDS if k in t} if isinstance(t, dict) else t for t in row]
            for row in farm["tiles"]
        ]
        farms.append(projected)
    market = {
        key: {p: obs["market"][key][p] for p in game.PRODUCTS} for key in ("inventory", "prices")
    }
    if any(type(n) is not int for n in market["inventory"].values()):
        raise ValueError("Market inventories must be integer-valued")
    if any(
        market["prices"][p] != game.market_price(p, market["inventory"][p]) for p in game.PRODUCTS
    ):
        raise ValueError("Public quotes differ from the default price curves")
    return {
        "player": obs["player"],
        "step": step,
        "day": obs["day"],
        "hour": obs["hour"],
        "farms": farms,
        "market": market,
        "town": {"unlocked_shops": list(obs["town"]["unlocked_shops"])},
        "private": {k: copy.deepcopy(obs["private"][k]) for k in ("shed", "seeds", "inventories")},
    }


def own_nonbuyable_sales(obs: dict[str, Any], action: dict[str, Any]) -> dict[str, int]:
    """Executed SELL units are known for non-buyable goods, regardless of quotes.

    Simulate only the legal own-farm phase, including atomic seed-request blocking.
    Other market orders cannot create these goods or prevent an affordable SELL.
    This predicts execution of our submitted action, not the opponent's action.
    """
    farm, private = copy.deepcopy((obs["farms"][obs["player"]], obs["private"]))
    actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
    requests = Counter(a[1] for a in actions if len(a) >= 2 and a[0] == "PLANT")
    blocked = {p for p, n in requests.items() if n > private["seeds"].get(p, 0)}
    for index, unit in enumerate(actions):
        if len(unit) >= 2 and unit[0] == "PLANT" and unit[1] in blocked:
            unit = ["PASS"]
        game._apply_unit_action(farm, private, index, unit, 10, obs["day"], 24, 100)
    sold = dict.fromkeys(BOUNDED_PRODUCTS, 0)
    for order in action.get("market", [])[:10]:
        parsed = game._parse_order(order)
        if parsed and parsed["type"] == "SELL" and parsed["item"] in sold:
            item = parsed["item"]
            amount = min(parsed["remaining"], private["shed"].get(item, 0))
            private["shed"][item] -= amount
            sold[item] += amount
    return sold


def possible_collection(previous: dict, current: dict) -> dict[str, int]:
    """Upper bound on newly harvested non-buyable units in the previous turn.

    A disappearing plant can be DIG, death, decay or HARVEST. We never equate it
    with collection. Workers can act only at their pre-action location. A second
    co-located worker may water before harvest; night growth is after harvesting.
    """
    rival = 1 - previous["player"]
    before, after = previous["farms"][rival], current["farms"][rival]
    occupancy = Counter(tuple(p) for p in [before["farmer"], *before["hands"]])
    units = dict.fromkeys(BOUNDED_PRODUCTS, 0)
    night = previous["hour"] == 23
    for (x, y), workers in occupancy.items():
        tile, new = before["tiles"][y][x], after["tiles"][y][x]
        if not isinstance(tile, dict) or tile.get("yield_units", 0) <= 0:
            continue
        same = False
        amount = tile["yield_units"]
        if tile.get("kind") == "PLANT":
            item = tile["crop"]
            params = game.CROPS[item]
            age = previous["day"] - tile["planted_day"]
            if age < params["first_yield_day"]:
                continue
            same = isinstance(new, dict) and all(
                new.get(k) == tile.get(k) for k in ("kind", "crop", "planted_day")
            )
            if not params["ongoing"]:
                if same:
                    continue  # A successful harvest would have removed this mature plant.
                if (
                    workers >= 2
                    and not tile["watered_today"]
                    and (params["max_yield_day"] + 1) // 2 <= age <= params["max_yield_day"]
                ):
                    amount = min(
                        params["max_yield"],
                        amount
                        + 1
                        + int(tile["fertilized_until_day"] >= previous["day"] or workers >= 3),
                    )
        elif tile.get("animal") in game.ANIMALS:
            item = game.ANIMALS[tile["animal"]]["product"]
            same = isinstance(new, dict) and all(
                new.get(k) == tile.get(k) for k in ("animal", "placed_day")
            )
        else:
            continue
        if item not in units:
            continue
        if same and not night and new.get("yield_units", 0) > 0:
            continue  # No same-day regeneration after successful ongoing/animal harvest.
        units[item] += amount
    return units


class MarketHistory:
    """observe(o_t) -> features; record_action(a_t); repeat, or serialize between calls.

    Every output uses at most o_t and a_(t-1). Consecutive callbacks are required;
    a new callback zero resets the episode. Cold starts after zero are rejected.
    """

    def __init__(self) -> None:
        self.current: dict[str, Any] | None = None
        self.pending_sales: dict[str, int] | None = None
        self.rows: list[dict[str, dict[str, float]]] = []
        self.upper = dict.fromkeys(BOUNDED_PRODUCTS, 0)
        self.last_sale: dict[str, int] = {}

    def observe(self, observation: dict[str, Any]) -> FeatureVector:
        obs = _snapshot(observation)
        if obs["step"] == 0:
            self.__init__()
        elif self.current is None:
            raise ValueError("History must start at callback zero; do not impute an empty rival")
        elif (
            obs["step"] != self.current["step"] + 1
            or obs["player"] != self.current["player"]
            or self.pending_sales is None
        ):
            raise ValueError("History requires consecutive same-player callbacks and own actions")
        if self.current is not None:
            self._advance(obs)
        self.current, self.pending_sales = obs, None
        return self._features()

    def record_action(self, action: dict[str, Any]) -> None:
        if self.current is None or self.pending_sales is not None:
            raise ValueError("Record exactly one own action after each observation")
        if not isinstance(action, dict) or not isinstance(action.get("hands", []), list):
            raise ValueError("Expected a dictionary action with a list of hand actions")
        actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
        if any(not isinstance(a, list) for a in actions) or not isinstance(
            action.get("market", []), list
        ):
            raise ValueError("Expected list-valued unit actions and market orders")
        self.pending_sales = own_nonbuyable_sales(self.current, action)

    def _advance(self, obs: dict[str, Any]) -> None:
        previous = self.current
        assert previous is not None and self.pending_sales is not None
        harvest = possible_collection(previous, obs)
        row: dict[str, dict[str, float]] = {}
        updated_upper = self.upper.copy()
        for item in game.PRODUCTS:
            old = previous["market"]["inventory"][item]
            demand = town_consumption(previous["town"]["unlocked_shops"], item, previous["step"], 1)
            post_market = obs["market"]["inventory"][item] + demand
            net = post_market - old
            supported = item in BOUNDED_PRODUCTS
            lower = upper = collected = censored = 0
            if supported:
                collected = harvest[item]
                stock = self.upper[item] + collected
                censored = int(game.market_price(item, post_market) == 1)
                lower = max(0, net - self.pending_sales[item])
                upper = min(100, stock) if censored else lower
                if (
                    net < 0
                    or lower > min(100, stock)
                    or (not censored and net < self.pending_sales[item])
                ):
                    raise ValueError(f"Public transition contradicts the {item} supply contract")
                updated_upper[item] = stock - lower
                if previous["hour"] == 23:
                    updated_upper[item] = min(100, updated_upper[item])
            row[item] = {
                "available": 1,
                "trade_net": net,
                "known_demand": demand,
                "quote_change": obs["market"]["prices"][item] - previous["market"]["prices"][item],
                "sale_supported": int(supported),
                "sales_lower": lower,
                "sales_upper": upper,
                "sales_identified": int(supported and lower == upper),
                "floor_censored": censored,
                "harvest_upper": collected,
                "stock_upper": updated_upper.get(item, 0),
            }
        self.upper = updated_upper
        for item in BOUNDED_PRODUCTS:
            if row[item]["sales_lower"] > 0:
                self.last_sale[item] = previous["step"]
        self.rows = [*self.rows, row][-max(WINDOWS) :]

    def _features(self) -> FeatureVector:
        assert self.current is not None
        result = FeatureVector()
        for item in game.PRODUCTS:
            base = (
                self.rows[-1][item]
                if self.rows
                else {
                    "available": 0,
                    "trade_net": 0,
                    "known_demand": 0,
                    "quote_change": 0,
                    "sale_supported": int(item in BOUNDED_PRODUCTS),
                    "sales_lower": 0,
                    "sales_upper": 0,
                    "sales_identified": 0,
                    "floor_censored": 0,
                    "harvest_upper": 0,
                    "stock_upper": 0,
                }
            )
            for name, value in base.items():
                result.add(f"market_history.{item}.last.{name}", value, "causal_supply_bounds")
            for window in WINDOWS:
                records = [row[item] for row in self.rows[-window:]]
                count = len(records)
                flow = sum(r["trade_net"] for r in records)
                mean = flow / count if count else 0
                values = {
                    "observed": count,
                    "trade_sum": flow,
                    "trade_std": math.sqrt(
                        sum((r["trade_net"] - mean) ** 2 for r in records) / count
                    )
                    if count
                    else 0,
                    "quote_change_sum": sum(r["quote_change"] for r in records),
                    "sales_lower_sum": sum(r["sales_lower"] for r in records),
                    "sales_upper_sum": sum(r["sales_upper"] for r in records),
                    "harvest_upper_sum": sum(r["harvest_upper"] for r in records),
                    "identified_fraction": sum(r["sales_identified"] for r in records) / count
                    if count
                    else 0,
                }
                for name, value in values.items():
                    result.add(
                        f"market_history.{item}.w{window}.{name}",
                        value,
                        "multiscale_market_history",
                    )
            seen = item in self.last_sale
            for name, value in {
                "sale_seen": int(seen),
                "sale_age": self.current["step"] - self.last_sale[item] if seen else 0,
            }.items():
                result.add(f"market_history.{item}.{name}", value, "rival_sale_recency")
        return result

    def to_json(self) -> str:
        payload = {
            "contract": CONTRACT,
            "current": self.current,
            "pending_sales": self.pending_sales,
            "rows": self.rows,
            "upper": self.upper,
            "last_sale": self.last_sale,
        }
        return canonical({"payload": payload, "sha256": digest(payload)}).decode()

    @classmethod
    def from_json(cls, serialized: str) -> "MarketHistory":
        envelope = json.loads(serialized)
        payload = envelope["payload"]
        if digest(payload) != envelope["sha256"] or payload["contract"] != CONTRACT:
            raise ValueError("History checksum or contract differs")
        if set(payload) != {"contract", "current", "pending_sales", "rows", "upper", "last_sale"}:
            raise ValueError("Unexpected history fields")
        if len(payload["rows"]) > max(WINDOWS) or set(payload["upper"]) != set(BOUNDED_PRODUCTS):
            raise ValueError("History shape differs")
        history = cls()
        for key in ("current", "pending_sales", "rows", "upper", "last_sale"):
            setattr(history, key, payload[key])
        if history.current is not None:
            if _snapshot(history.current) != history.current:
                raise ValueError("Serialized observation contains non-contract fields")
            history._features()  # Reject non-finite or incomplete feature payloads.
        return history
