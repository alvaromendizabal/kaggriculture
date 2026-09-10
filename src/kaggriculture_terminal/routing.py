"""Observation-only, bounded collection/delivery routes with joint task exclusion.

Routes contain zero, one or two collections, optionally WATER before a harvest,
then one capacity-safe DROP. Exact assignment is over the retained route menu,
not over all possible game plans. Prices are current no-opponent-sale scenarios.
"""

import copy
from dataclasses import dataclass
from itertools import permutations

from kaggriculture_livestock.features import located
from kaggriculture_research.crop_policy import SHED, distance, move_toward
from kaggriculture_research.environment import game
from kaggriculture_research.features import FeatureVector, sale_revenue
from kaggriculture_research.market_features import project_observation
from kaggriculture_research.relationship_features import ready_units

ITEMS = tuple(sorted(game.PRODUCTS))
MENU = 8
WORK_VALUE = 8.0


@dataclass(frozen=True)
class Collection:
    resource: tuple[int, int, str]
    target: tuple[int, int]
    commands: tuple[tuple, ...]
    item: str
    units: int


@dataclass(frozen=True)
class Route:
    resources: frozenset
    actions: tuple[tuple, ...]
    quantities: tuple[int, ...]
    value: float

    @property
    def utility(self) -> float:
        return self.value - WORK_VALUE * len(self.actions)


def collections(obs: dict) -> list[Collection]:
    result = []
    for x, y, tile in located(obs["farms"][obs["player"]]):
        target = (x, y)
        units = ready_units(tile, obs["day"])
        if tile.get("animal"):
            units = tile["yield_units"]
        if units:
            item = game.ANIMALS[tile["animal"]]["product"] if tile.get("animal") else tile["crop"]
            resource = (x, y, "HARVEST")
            result.append(Collection(resource, target, (("HARVEST",),), item, units))
            if tile.get("kind") == "PLANT" and not tile["watered_today"]:
                params = game.CROPS[item]
                age = obs["day"] - tile["planted_day"]
                if (
                    not params["ongoing"]
                    and (params["max_yield_day"] + 1) // 2 <= age <= params["max_yield_day"]
                ):
                    bonus = 2 if tile["fertilized_until_day"] >= obs["day"] else 1
                    extra = min(bonus, params["max_yield"] - units)
                    if extra > 0:
                        result.append(
                            Collection(
                                resource, target, (("WATER",), ("HARVEST",)), item, units + extra
                            )
                        )
        if tile.get("animal") and tile["fertilizer_available"]:
            result.append(
                Collection((x, y, "MANURE"), target, (("COLLECT_FERTILIZER",),), "FERTILIZER", 1)
            )
    return result


def walk(position: tuple, target: tuple) -> tuple[list[tuple], tuple]:
    actions = []
    while position != target:
        action = tuple(move_toward(position, target))
        dx, dy = game.FARMER_MOVES[action[0]]
        position = (position[0] + dx, position[1] + dy)
        actions.append(action)
    return actions, position


def menus(obs: dict) -> tuple[list[list[Route]], dict]:
    farm, private = obs["farms"][obs["player"]], obs["private"]
    tasks = collections(obs)
    budget = min(23, max(0, 719 - obs["step"]))
    room = max(0, 100 - sum(private["shed"].values()))
    result, all_count, feasible = [], 0, 0
    for unit in range(1 + len(farm["hands"])):
        position = tuple(game._farmer_position(farm, unit))
        carried = private["inventories"][unit]
        options = []
        paths = [(), *((t,) for t in tasks), *permutations(tasks, 2)]
        for path in paths:
            if len({t.resource for t in path}) != len(path):
                continue
            all_count += 1
            quantities = {item: carried.get(item, 0) for item in ITEMS}
            actions, current = [], position
            for task in path:
                moves, current = walk(current, task.target)
                actions.extend(moves)
                actions.extend(task.commands)
                quantities[task.item] += task.units
            # DROP would also deposit non-products; exclude such routes entirely.
            if any(n for item, n in carried.items() if item not in ITEMS):
                continue
            if not sum(quantities.values()) or sum(quantities.values()) > room:
                continue
            shed = min(SHED, key=lambda s: (distance(current, s), s))
            moves, _ = walk(current, shed)
            actions.extend(moves)
            actions.append(("DROP",))
            if len(actions) > budget:
                continue
            feasible += 1
            value = sum(
                sale_revenue(i, obs["market"]["inventory"][i], q) for i, q in quantities.items()
            )
            options.append(
                Route(
                    frozenset(t.resource for t in path),
                    tuple(actions),
                    tuple(quantities[i] for i in ITEMS),
                    value,
                )
            )
        options.sort(key=lambda r: (-r.utility, len(r.actions), r.actions))
        # A feasible direct deposit must survive pruning; PASS enables conflict resolution.
        retained = options[:MENU]
        direct = next((r for r in options if not r.resources), None)
        if direct is not None and direct not in retained:
            retained[-1:] = [direct]
        retained.append(Route(frozenset(), (), (0,) * len(ITEMS), 0.0))
        result.append(retained)
    return result, {
        "routes_generated": all_count,
        "routes_feasible": feasible,
        "routes_retained": sum(len(m) - 1 for m in result),
        "resources": len({t.resource for t in tasks}),
        "room": room,
        "budget": budget,
    }


def assign(menu: list[list[Route]], room: int, obs: dict) -> tuple[list[Route], dict]:
    """Enumerate the small menu product with exact resource/capacity constraints."""
    best, best_key, leaves = [], None, 0
    prices = obs["market"]["inventory"]
    curves = {i: [sale_revenue(i, prices[i], q) for q in range(room + 1)] for i in ITEMS}

    def visit(unit, used, quantities, selected, work):
        nonlocal best, best_key, leaves
        if unit == len(menu):
            leaves += 1
            value = sum(curves[i][q] for i, q in zip(ITEMS, quantities, strict=True))
            key = (value - WORK_VALUE * work, -work)
            if best_key is None or key > best_key:
                best, best_key = list(selected), key
            return
        for route in menu[unit]:
            if used & route.resources:
                continue
            combined = tuple(a + b for a, b in zip(quantities, route.quantities, strict=True))
            if sum(combined) <= room:
                visit(
                    unit + 1,
                    used | route.resources,
                    combined,
                    [*selected, route],
                    work + len(route.actions),
                )

    visit(0, frozenset(), (0,) * len(ITEMS), [], 0)
    return best, {
        "assignment_leaves": leaves,
        "joint_utility": best_key[0],
        "joint_work": -best_key[1],
        "joint_units": sum(sum(r.quantities) for r in best),
    }


def liquidation(observation: dict) -> tuple[dict, dict]:
    obs = copy.deepcopy(project_observation(observation))
    if obs["day"] != 29:
        raise ValueError("Liquidation policy is registered for the final day only")
    menu, diagnostics = menus(obs)
    routes, joint = assign(menu, diagnostics["room"], obs)
    diagnostics.update(joint)
    farm, private = obs["farms"][obs["player"]], obs["private"]
    actions, noops = [], 0
    for unit, route in enumerate(routes):
        action = list(route.actions[0]) if route.actions else ["PASS"]
        before = copy.deepcopy((farm, private))
        game._apply_unit_action(farm, private, unit, action, 10, obs["day"], 24, 100)
        noops += int(action[0] != "PASS" and before == (farm, private))
        actions.append(action)
    orders = [["SELL", i, private["shed"][i]] for i in ITEMS if private["shed"].get(i, 0)]
    diagnostics["ineffective_farm_actions"] = noops
    return {"farmer": actions[0], "hands": actions[1:], "market": orders}, diagnostics


def terminal_features(observation: dict) -> FeatureVector:
    obs, f = project_observation(observation), FeatureVector()
    farm, private = obs["farms"][obs["player"]], obs["private"]
    remaining = max(0, 719 - obs["step"])
    terminal = obs["day"] == 29
    horizon = {
        "decisions_remaining": remaining,
        "refreshes_remaining": max(0, 29 - obs["day"]),
        "final_day": int(terminal),
        "next_refresh_exists": int(obs["day"] < 29),
    }
    for name, value in horizon.items():
        f.add("terminal." + name, value, "terminal_event_feasibility")
    tasks = collections(obs)
    for item in ITEMS:
        values = {
            "carried": sum(inv.get(item, 0) for inv in private["inventories"]),
            "shed": private["shed"].get(item, 0),
            "ready": sum(t.units for t in tasks if t.item == item and len(t.commands) == 1),
        }
        values["carry_sale_value"] = sale_revenue(
            item, obs["market"]["inventory"][item], values["carried"]
        )
        for name, value in values.items():
            f.add(f"terminal.{item}.{name}", value, "terminal_stock_opportunity")
    for animal in sorted(game.ANIMALS):
        tiles = [t for _, _, t in located(farm) if t.get("animal") == animal]
        values = {
            "unfed_without_refresh": sum(not t["fed_today"] for t in tiles) * terminal,
            "bank_without_conversion": sum(t["pending_care_bonus"] for t in tiles) * terminal,
            "stored_units": sum(t["yield_units"] for t in tiles),
        }
        for name, value in values.items():
            f.add(f"terminal.{animal}.{name}", value, "terminal_event_feasibility")
    # Expensive joint menu is explicitly inactive before the final day.
    menu, stats = menus(obs) if terminal else ([], {})
    if terminal:
        _, joint = assign(menu, stats["room"], obs)
        stats.update(joint)
    for name in (
        "routes_generated",
        "routes_feasible",
        "routes_retained",
        "resources",
        "room",
        "budget",
        "assignment_leaves",
        "joint_utility",
        "joint_work",
        "joint_units",
    ):
        f.add("terminal." + name, stats.get(name, 0), "joint_liquidation_routes")
    for unit in range(4):
        routes = menu[unit] if unit < len(menu) else []
        values = {
            "present": int(unit < 1 + len(farm["hands"])),
            "menu_size": max(0, len(routes) - 1),
            "best_value": max((r.value for r in routes), default=0),
            "best_utility": max((r.utility for r in routes), default=0),
            "minimum_route_actions": min((len(r.actions) for r in routes if r.actions), default=0),
        }
        for name, value in values.items():
            f.add(f"terminal.worker{unit}.{name}", value, "joint_liquidation_routes")
    return f
