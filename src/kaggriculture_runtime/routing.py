"""Linear-time price curves for the unchanged bounded route assignment problem.

The frozen Study 6/7 implementation builds each quantity's revenue from scratch.
Here every prefix shares the same legal immediate-sale trajectory. Enumeration,
capacity constraints, menu order, and tie-breaking are unchanged. This is a
runtime candidate: adding it does not change the registered staffing policy.
"""

from collections.abc import Callable
from typing import Any


def revenue_curve(item: str, inventory: int, maximum: int, price_function: Callable) -> list[float]:
    """Match independent sale_revenue(q) calls for q=0..maximum in O(maximum)."""
    if not isinstance(maximum, int) or maximum < 0:
        raise ValueError("maximum must be a nonnegative integer")
    curve = [0.0]
    total = 0.0
    for _ in range(maximum):
        price = price_function(item, inventory)
        total += price
        inventory += int(price > 1)
        curve.append(total)
    return curve


def exact_assignment(
    menu: list[list[Any]],
    room: int,
    prices: dict,
    items: tuple,
    work_value: float,
    price_function: Callable,
) -> tuple[list[Any], dict]:
    """Keep the frozen DFS order and exact exclusion/capacity/tie semantics."""
    curves = {i: revenue_curve(i, prices[i], room, price_function) for i in items}
    best, best_key, leaves = [], None, 0

    def visit(unit, used, quantities, selected, work):
        nonlocal best, best_key, leaves
        if unit == len(menu):
            leaves += 1
            value = sum(curves[i][q] for i, q in zip(items, quantities, strict=True))
            key = (value - work_value * work, -work)
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

    visit(0, frozenset(), (0,) * len(items), [], 0)
    if best_key is None:
        raise ValueError("No feasible assignment; the menu must include PASS")
    return best, {
        "assignment_leaves": leaves,
        "joint_utility": best_key[0],
        "joint_work": -best_key[1],
        "joint_units": sum(sum(route.quantities) for route in best),
    }


def assign(menu: list[list[Any]], room: int, obs: dict) -> tuple[list[Any], dict]:
    """Adapter used only by explicitly selected runtime/behavior-equivalence tests."""
    from kaggriculture_research.environment import game
    from kaggriculture_terminal.routing import ITEMS, WORK_VALUE

    return exact_assignment(
        menu, room, obs["market"]["inventory"], ITEMS, WORK_VALUE, game.market_price
    )
