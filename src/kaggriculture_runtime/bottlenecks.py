"""Exact counterfactual values on a bounded legal terminal-route menu.

These are discrete removal/sensitivity values, not LP duals or forecasts. All
counterfactuals use the same retained menu: they cannot value ungenerated routes.
No seed, outcome, hidden inventory or future observation enters this interface.
"""

from collections.abc import Callable
from itertools import product
from math import isfinite
from typing import Any

from kaggriculture_runtime.routing import revenue_curve

WORKERS = 4
CAPACITY_DELTAS = (-10, -5, -1, 1, 5, 10)


def assignment_bottlenecks(
    menu: list[list[Any]],
    room: int,
    prices: dict,
    items: tuple,
    price_function: Callable,
    work_value: float = 8.0,
) -> dict[str, float]:
    """Enumerate at most 9**4 plans once and measure the binding constraints.

    Tie breaking matches the frozen depth-first solver. Worker removal means
    forcing that unit to its PASS route. Resource removal forbids collection
    of that resource, not removal of already carried goods. Capacity expansion
    is hypothetical sensitivity over the retained menu, not a legal game action.
    """
    if not isinstance(room, int) or not 0 <= room <= 100:
        raise ValueError("room must be an integer in 0..100")
    if not 1 <= len(menu) <= WORKERS or any(not 1 <= len(m) <= 9 for m in menu):
        raise ValueError("Expected 1..4 workers with 1..9 retained routes each")
    if not items or len(items) != len(set(items)) or not isfinite(work_value) or work_value < 0:
        raise ValueError("Invalid item schema or work valuation")
    limit = min(100, room + 10)
    curves = {i: revenue_curve(i, prices[i], limit, price_function) for i in items}
    for routes in menu:
        if not any(not r.actions and not r.resources and not any(r.quantities) for r in routes):
            raise ValueError("Each worker needs a zero-quantity PASS route")
        for route in routes:
            if len(route.quantities) != len(items) or any(
                not isinstance(q, int) or q < 0 for q in route.quantities
            ):
                raise ValueError("Invalid route quantities")
    plans = []
    for indices in product(*(range(len(routes)) for routes in menu)):
        chosen = [menu[u][index] for u, index in enumerate(indices)]
        used = frozenset()
        conflict = False
        for route in chosen:
            if used & route.resources:
                conflict = True
                break
            used |= route.resources
        if conflict:
            continue
        quantities = tuple(sum(r.quantities[j] for r in chosen) for j in range(len(items)))
        units = sum(quantities)
        if units > limit:
            continue
        work = sum(len(r.actions) for r in chosen)
        revenue = sum(curves[i][q] for i, q in zip(items, quantities, strict=True))
        plans.append(
            {
                "key": (revenue - work_value * work, -work),
                "indices": indices,
                "units": units,
                "used": used,
                "active": tuple(bool(r.actions) for r in chosen),
                "revenue": revenue,
            }
        )
    feasible = [p for p in plans if p["units"] <= room]
    best = max(feasible, key=lambda p: p["key"])
    utility = best["key"][0]
    alternatives = [p for p in feasible if p["indices"] != best["indices"]]
    second = max(alternatives, key=lambda p: p["key"], default=best)
    lower = [p["key"][0] for p in feasible if p["key"][0] < utility]
    values = {
        "active": 1,
        "workers": len(menu),
        "feasible_plans": len(feasible),
        "best_utility": utility,
        "best_revenue": best["revenue"],
        "best_work": -best["key"][1],
        "best_units": best["units"],
        "storage_slack": room - best["units"],
        "selected_resources": len(best["used"]),
        "optimal_plan_count": sum(p["key"] == best["key"] for p in feasible),
        "runner_up_utility_gap": utility - second["key"][0],
        "next_lower_utility_gap": utility - max(lower, default=utility),
        "runner_up_worker_changes": sum(
            a != b for a, b in zip(best["indices"], second["indices"], strict=True)
        ),
    }
    for delta in CAPACITY_DELTAS:
        capacity = min(100, max(0, room + delta))
        attainable = max(p["key"][0] for p in plans if p["units"] <= capacity)
        label = ("minus" if delta < 0 else "plus") + str(abs(delta))
        values[f"capacity_{label}_utility_delta"] = attainable - utility
        values[f"capacity_{label}_actual_units"] = capacity - room
    for unit in range(WORKERS):
        present = unit < len(menu)
        remaining = (
            max((p["key"][0] for p in feasible if not p["active"][unit]), default=utility)
            if present
            else utility
        )
        values[f"worker{unit}_present"] = int(present)
        values[f"worker{unit}_removal_loss"] = utility - remaining
    resources = set().union(*(p["used"] for p in feasible))
    losses = [
        utility - max(p["key"][0] for p in feasible if resource not in p["used"])
        for resource in resources
    ]
    positive = [v for v in losses if v > 0]
    values.update(
        {
            "available_resources": len(resources),
            "critical_resources": len(positive),
            "resource_loss_max": max(losses, default=0),
            "resource_loss_sum": sum(losses),
            "resource_loss_mean": sum(losses) / len(losses) if losses else 0,
            "resource_loss_concentration": max(losses, default=0) / sum(losses)
            if sum(losses)
            else 0,
        }
    )
    result = {"bottleneck." + k: float(v) for k, v in values.items()}
    if not all(isfinite(value) for value in result.values()):
        raise ValueError("Non-finite bottleneck descriptor")
    return result
