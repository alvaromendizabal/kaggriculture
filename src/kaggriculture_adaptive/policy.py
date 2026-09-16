"""Adaptive overlay for Kaggriculture public-route research.

The policy deliberately keeps low-level route execution stable and adds sparse,
observation-driven interventions at high-value decision points:

* exact market price-impact ordering inside existing SELL slots;
* public-state near-mirror detection;
* clone-gated one-step premium front-running with next-step repayment;
* observation-driven terminal harvest/drop/liquidation.

The public route supplied to this class remains an external research baseline.
This module contains the authored adaptive overlay only.
"""

from __future__ import annotations

import collections
import copy
import math
from collections.abc import Callable
from dataclasses import dataclass, field

SELLABLE = (
    "STRAWBERRY",
    "MELON",
    "MILK",
    "WOOL",
    "EGG",
    "TOMATO",
    "CARROT",
    "WHEAT",
    "FERTILIZER",
)
PREMIUM = ("MELON", "STRAWBERRY", "MILK", "WOOL")
PRICE_FLOOR = 1
MARKET_PARAMS = {
    "WHEAT": (25, 10000, 400, "sqrt", 0.8, "log", 0.2),
    "CARROT": (35, 10000, 450, "log", 0.2, "sqrt", 0.7),
    "TOMATO": (60, 10000, 200, "linear", 0.4, "sqrt", 0.6),
    "STRAWBERRY": (120, 10000, 100, "sqrt", 0.7, "linear", 1.6),
    "MELON": (250, 10000, 300, "log", 0.2, "sq", 3.6),
    "EGG": (50, 10000, 332, "linear", 0.4, "log", 0.2),
    "MILK": (160, 10000, 122, "sqrt", 0.6, "linear", 1.6),
    "WOOL": (200, 10000, 105, "log", 0.2, "sq", 3.2),
    "FERTILIZER": (100, 10000, 200, "linear", 0.4, "linear", 0.4),
}
SHOP_PRODUCTS = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}

MODES = ("impact_slots", "clone_front_run", "clone_terminal")


def _shape(name: str, value: float) -> float:
    value = max(0.0, float(value))
    if name == "linear":
        return value
    if name == "sq":
        return value * value
    if name == "sqrt":
        return math.sqrt(value)
    if name == "log":
        return math.log1p(value)
    if name == "log10":
        return math.log10(1.0 + value)
    raise ValueError(name)


def market_price(item: str, inventory: int) -> int:
    base, equilibrium, scale, below_f, below_t, above_f, above_t = MARKET_PARAMS[item]
    inventory = int(inventory)
    if inventory < equilibrium:
        amplitude = below_t * base / _shape(below_f, scale)
        price = base + amplitude * _shape(below_f, equilibrium - inventory)
    else:
        amplitude = above_t * base / _shape(above_f, scale)
        price = base - amplitude * _shape(above_f, inventory - equilibrium)
    return max(PRICE_FLOOR, int(round(price)))


def sale_revenue(item: str, inventory: int, quantity: int) -> float:
    total = 0.0
    inv = int(inventory)
    for _ in range(max(0, int(quantity))):
        price = market_price(item, inv)
        total += price
        inv += int(price > PRICE_FLOOR)
    return total


def impact_loss(item: str, inventory: int, quantity: int) -> float:
    """Revenue lost if an equal-sized competing sale lands immediately before ours."""
    quantity = max(0, int(quantity))
    if quantity <= 0:
        return 0.0
    first = sale_revenue(item, inventory, quantity)
    inv_after_competitor = int(inventory)
    for _ in range(quantity):
        price = market_price(item, inv_after_competitor)
        inv_after_competitor += int(price > PRICE_FLOOR)
    second = sale_revenue(item, inv_after_competitor, quantity)
    return max(0.0, first - second)


def _copy_action(action: dict | None) -> dict:
    action = copy.deepcopy(action or {})
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(x or ["PASS"]) for x in (action.get("hands") or [])],
        "market": [list(x) for x in (action.get("market") or [])],
    }


def _effective_step(obs: dict, config=None) -> int:
    """Return a seat-safe episode clock.

    kaggle-environments 1.32.7 does not populate ``obs["step"]`` for seat 1.
    ``day`` and ``hour`` are synchronized for both seats, so prefer that public
    clock whenever it is available and fall back to ``step`` only for synthetic
    or legacy observations.
    """
    turns_per_day = 24
    if config is not None:
        try:
            turns_per_day = int(config.get("turnsPerDay", turns_per_day) or turns_per_day)
        except (AttributeError, TypeError, ValueError):
            try:
                turns_per_day = int(getattr(config, "turnsPerDay", turns_per_day) or turns_per_day)
            except (AttributeError, TypeError, ValueError):
                turns_per_day = 24
    turns_per_day = max(1, turns_per_day)

    day = obs.get("day")
    hour = obs.get("hour")
    if day is not None and hour is not None:
        return max(0, int(day)) * turns_per_day + max(0, int(hour))

    return max(0, int(obs.get("step", 0) or 0))

def _seat(obs: dict) -> int:
    return 1 if int(obs.get("player", 0) or 0) == 1 else 0


def _farm(obs: dict, seat: int) -> dict:
    farms = obs.get("farms") or []
    return farms[seat] if seat < len(farms) else {}


def _align_hands(action: dict, obs: dict) -> dict:
    action = _copy_action(action)
    expected = len(_farm(obs, _seat(obs)).get("hands", []) or [])
    hands = list(action.get("hands") or [])
    if len(hands) < expected:
        hands.extend([["PASS"] for _ in range(expected - len(hands))])
    action["hands"] = hands[:expected]
    return action


def public_signature(farm: dict) -> tuple:
    counts = collections.Counter()
    for row in farm.get("tiles", []) or []:
        for tile in row or []:
            if not isinstance(tile, dict):
                continue
            for key in ("animal", "crop", "kind"):
                value = tile.get(key)
                if value:
                    counts[str(value)] += 1
    keys = (
        "COW",
        "SHEEP",
        "GOOSE",
        "WHEAT",
        "CARROT",
        "TOMATO",
        "STRAWBERRY",
        "MELON",
        "PASTURE",
        "COOP",
        "WEED",
    )
    return (
        len(farm.get("hands", []) or []),
        len(farm.get("unlocked_quadrants", []) or []),
        tuple(counts[k] for k in keys),
    )


def signature_distance(left: tuple, right: tuple) -> float:
    return (
        abs(left[0] - right[0])
        + 3 * abs(left[1] - right[1])
        + sum(abs(a - b) for a, b in zip(left[2], right[2], strict=True))
    )


def _town_demand_now(obs: dict, item: str, step: int) -> int:
    demand = int(item != "FERTILIZER" and step % 24 == 0)
    if step % 4:
        return demand
    shops = (obs.get("town") or {}).get("unlocked_shops", []) or []
    for shop in shops:
        products = SHOP_PRODUCTS.get(shop, ())
        if item in products:
            demand += 2 if len(products) == 1 else 1
    return demand


def _pickup_reserve(action: dict, item: str) -> int:
    reserve = 0
    unit_actions = [action.get("farmer", ["PASS"]), *(action.get("hands") or [])]
    for order in unit_actions:
        if (
            isinstance(order, list)
            and len(order) >= 2
            and order[0] == "PICKUP"
            and order[1] == item
        ):
            reserve += max(0, int(order[2])) if len(order) >= 3 else 1
    return reserve


def _existing_sell(action: dict, item: str) -> int:
    return sum(
        max(0, int(order[2]))
        for order in action.get("market", []) or []
        if isinstance(order, list) and len(order) >= 3 and order[0] == "SELL" and order[1] == item
    )


def rank_existing_sell_slots(obs: dict, action: dict) -> tuple[dict, bool]:
    """Reorder only existing SELL positions; non-SELL slot locations never move."""
    action = _copy_action(action)
    market = list(action.get("market") or [])
    inventory = (obs.get("market") or {}).get("inventory") or {}
    rows = []
    for idx, order in enumerate(market):
        if not (
            isinstance(order, list)
            and len(order) >= 3
            and order[0] == "SELL"
            and order[1] in MARKET_PARAMS
        ):
            continue
        item = str(order[1])
        qty = max(0, int(order[2]))
        inv = int(inventory.get(item, 10000) or 10000)
        rows.append((impact_loss(item, inv, qty), -idx, list(order)))

    if len(rows) < 2:
        return action, False

    rows.sort(reverse=True)
    ranked = iter(row[2] for row in rows)
    updated = [
        next(ranked)
        if (
            isinstance(order, list)
            and len(order) >= 3
            and order[0] == "SELL"
            and order[1] in MARKET_PARAMS
        )
        else order
        for order in market
    ]
    changed = updated != market
    action["market"] = updated[:10]
    return action, changed


def _shed_access(size: int) -> set[tuple[int, int]]:
    half = size // 2
    return {
        (half - 1, half - 1),
        (half, half - 1),
        (half - 1, half),
        (half, half),
    }


def _move_toward(pos: tuple[int, int], target: tuple[int, int], tiles: list) -> list:
    x, y = pos
    tx, ty = target
    candidates = []
    if tx < x:
        candidates.append(("WEST", (x - 1, y)))
    if tx > x:
        candidates.append(("EAST", (x + 1, y)))
    if ty < y:
        candidates.append(("NORTH", (x, y - 1)))
    if ty > y:
        candidates.append(("SOUTH", (x, y + 1)))
    size = len(tiles)
    for op, (nx, ny) in candidates:
        if 0 <= nx < size and 0 <= ny < size and tiles[ny][nx] != "LOCKED":
            return [op]
    return ["PASS"]


def terminal_controller(obs: dict) -> dict:
    """Final-three-turn controller: harvest, return carried goods, and liquidate."""
    seat = _seat(obs)
    farm = _farm(obs, seat)
    private = obs.get("private") or {}
    tiles = farm.get("tiles") or []
    size = len(tiles)
    positions = [farm.get("farmer", [0, 0]), *(farm.get("hands") or [])]
    inventories = list(private.get("inventories") or [])
    inventories.extend({} for _ in range(max(0, len(positions) - len(inventories))))
    sheds = _shed_access(size)

    harvestable = {
        (x, y)
        for y, row in enumerate(tiles)
        for x, tile in enumerate(row)
        if isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0
    }

    unit_actions = []
    pending = collections.Counter()
    for raw_pos, inv in zip(positions, inventories, strict=False):
        pos = tuple(raw_pos)
        inv = inv or {}
        load = sum(max(0, int(v or 0)) for v in inv.values())
        x, y = pos
        tile = tiles[y][x] if 0 <= y < size and 0 <= x < size else None

        if load > 0 and pos in sheds:
            action = ["DROP"]
            for item, qty in inv.items():
                if item in SELLABLE:
                    pending[item] += max(0, int(qty or 0))
        elif isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0:
            action = ["HARVEST"]
            harvestable.discard(pos)
        elif load > 0 and sheds:
            target = min(sheds, key=lambda q: abs(q[0] - x) + abs(q[1] - y))
            action = _move_toward(pos, target, tiles)
        elif harvestable:
            target = min(
                harvestable,
                key=lambda q: (abs(q[0] - x) + abs(q[1] - y), q[1], q[0]),
            )
            harvestable.discard(target)
            action = _move_toward(pos, target, tiles)
        elif isinstance(tile, dict) and tile.get("fertilizer_available", False):
            action = ["COLLECT_FERTILIZER"]
        else:
            action = ["PASS"]
        unit_actions.append(action)

    shed = collections.Counter(private.get("shed") or {})
    shed.update(pending)
    market_inventory = (obs.get("market") or {}).get("inventory") or {}

    sells = []
    for item in SELLABLE:
        qty = max(0, int(shed.get(item, 0) or 0))
        if qty <= 0:
            continue
        inv = int(market_inventory.get(item, 10000) or 10000)
        sells.append((sale_revenue(item, inv, qty), item, qty))
    sells.sort(reverse=True)
    market = [["SELL", item, qty] for _, item, qty in sells[:10]]

    return {
        "farmer": unit_actions[0] if unit_actions else ["PASS"],
        "hands": unit_actions[1:],
        "market": market,
    }


@dataclass
class OverlayState:
    last_step: int = -1
    clone_confidence: int = 0
    due_step: int = -1
    due: dict[str, int] = field(default_factory=dict)


class AdaptiveOverlay:
    def __init__(
        self,
        base_agent: Callable,
        route: list[dict],
        mode: str = "impact_slots",
    ) -> None:
        if mode not in MODES:
            raise ValueError(f"Unknown mode: {mode}")
        self.base_agent = base_agent
        self.route = route
        self.mode = mode
        self.state = {0: OverlayState(), 1: OverlayState()}
        self.diagnostics = collections.Counter()

    def _episode_state(self, obs: dict, step: int) -> OverlayState:
        seat = _seat(obs)
        state = self.state[seat]
        if step == 0 or step <= state.last_step:
            state = OverlayState(last_step=step)
            self.state[seat] = state
        state.last_step = step
        if 0 <= state.due_step < step:
            state.due_step = -1
            state.due = {}
        return state

    def _update_clone_confidence(self, obs: dict, step: int, state: OverlayState) -> None:
        if step not in (4, 24) and not (step >= 48 and step % 24 == 0):
            return
        farms = obs.get("farms") or []
        if len(farms) < 2:
            return
        seat = _seat(obs)
        distance = signature_distance(
            public_signature(farms[seat]),
            public_signature(farms[1 - seat]),
        )
        self.diagnostics["clone_checks"] += 1
        if distance <= 1:
            state.clone_confidence = min(8, state.clone_confidence + 1)
        elif distance <= 4:
            state.clone_confidence = max(0, state.clone_confidence - 1)
        else:
            state.clone_confidence = max(0, state.clone_confidence - 3)
        self.diagnostics["clone_confidence_max"] = max(
            self.diagnostics["clone_confidence_max"],
            state.clone_confidence,
        )

    def _repay(self, action: dict, step: int, state: OverlayState) -> dict:
        if state.due_step != step or not state.due:
            return action
        action = _copy_action(action)
        due = dict(state.due)
        market = []
        repaid = 0
        for raw in action.get("market") or []:
            order = list(raw)
            if len(order) >= 3 and order[0] == "SELL" and order[1] in due and due[order[1]] > 0:
                requested = max(0, int(order[2]))
                reduction = min(requested, due[order[1]])
                requested -= reduction
                due[order[1]] -= reduction
                repaid += reduction
                if requested <= 0:
                    continue
                order[2] = requested
            market.append(order)
        action["market"] = market[:10]
        state.due_step = -1
        state.due = {}
        self.diagnostics["repaid_units"] += repaid
        return action

    def _front_run(self, obs: dict, action: dict, step: int, state: OverlayState) -> dict:
        if state.clone_confidence < 2 or step + 1 >= len(self.route):
            return action

        future = self.route[step + 1] or {}
        planned = collections.Counter()
        for order in future.get("market", []) or []:
            if (
                isinstance(order, list)
                and len(order) >= 3
                and order[0] == "SELL"
                and order[1] in PREMIUM
            ):
                planned[order[1]] += max(0, int(order[2]))

        if not planned:
            return action

        action = _copy_action(action)
        market = list(action.get("market") or [])
        if len(market) >= 10:
            return action

        shed = (obs.get("private") or {}).get("shed") or {}
        inventory = (obs.get("market") or {}).get("inventory") or {}
        choices = []

        for item, target in planned.items():
            if _town_demand_now(obs, item, step) > 0:
                continue
            available = (
                max(0, int(shed.get(item, 0) or 0))
                - _pickup_reserve(action, item)
                - _existing_sell(action, item)
            )
            quantity = min(target, max(0, available))
            if quantity <= 0:
                continue
            inv = int(inventory.get(item, 10000) or 10000)
            choices.append((impact_loss(item, inv, quantity), item, quantity))

        if not choices:
            return action

        _, item, quantity = max(choices)
        market.append(["SELL", item, quantity])
        action["market"] = market[:10]
        state.due_step = step + 1
        state.due = {item: quantity}
        self.diagnostics["front_run_events"] += 1
        self.diagnostics["front_run_units"] += quantity
        return action

    def __call__(self, obs: dict, config=None) -> dict:
        step = _effective_step(obs, config)
        state = self._episode_state(obs, step)

        if self.mode == "clone_terminal" and step >= 717:
            self.diagnostics["terminal_guard_steps"] += 1
            return _align_hands(terminal_controller(obs), obs)

        base = _copy_action(self.base_agent(obs, config))
        self._update_clone_confidence(obs, step, state)
        base = self._repay(base, step, state)

        ranked, changed = rank_existing_sell_slots(obs, base)
        if changed:
            self.diagnostics["slot_reorders"] += 1
        action = ranked

        if self.mode in ("clone_front_run", "clone_terminal"):
            action = self._front_run(obs, action, step, state)

        return _align_hands(action, obs)
