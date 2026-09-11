"""Observation-safe descriptors for staffing-controlled terminal assignment.

These features describe *why* multiple workers may help: route opportunity,
resource conflict, capacity, task concentration and marginal worker value. They
never use rewards, hidden opponent inventory, future shops or evaluator state.
The expensive route menu is active on the final day only.
"""

from __future__ import annotations

from itertools import combinations

from kaggriculture_research.features import FeatureVector
from kaggriculture_research.market_features import project_observation
from kaggriculture_terminal.routing import ITEMS, Route, assign, menus

WORKER_SLOTS = 4
WORKER_FIELDS = (
    "present",
    "menu_size",
    "best_utility",
    "second_best_utility",
    "best_value",
    "best_actions",
    "best_units",
)
GLOBAL_FIELDS = (
    "active_units",
    "hired_hands",
    "final_day",
    "hiring_window_open",
    "decisions_remaining",
    "shed_room",
    "route_resources",
    "routes_feasible",
    "routes_retained",
    "assignment_leaves",
    "joint_utility",
    "joint_work",
    "joint_units",
    "independent_route_utility",
    "optimistic_coordination_gap",
    "resource_conflict_pairs",
    "active_routed_workers",
    "max_assigned_work",
    "min_assigned_work",
    "max_assigned_units",
    "min_assigned_units",
)
MARGINAL_FIELDS = tuple(f"joint_utility_first_{n}_workers" for n in range(1, WORKER_SLOTS + 1))
FEATURE_COUNT = len(GLOBAL_FIELDS) + WORKER_SLOTS * len(WORKER_FIELDS) + len(MARGINAL_FIELDS)


def route_units(route: Route) -> int:
    """Return product units represented by one route."""
    return int(sum(route.quantities))


def best_nonpass(routes: list[Route]) -> list[Route]:
    """Rank non-PASS routes with the same deterministic ordering as routing.py."""
    return sorted(
        (route for route in routes if route.actions),
        key=lambda route: (-route.utility, len(route.actions), route.actions),
    )


def staffing_features(observation: dict) -> FeatureVector:
    """Build a fixed-schema worker/assignment representation from the legal observation."""
    obs = project_observation(observation)
    farm = obs["farms"][obs["player"]]
    active_units = 1 + len(farm["hands"])
    terminal = obs["day"] == 29
    vector = FeatureVector()

    menu: list[list[Route]] = []
    selected: list[Route] = []
    stats: dict[str, float] = {}
    joint: dict[str, float] = {}
    ranked: list[list[Route]] = []
    conflict_pairs = 0
    independent = 0.0
    marginal = {name: 0.0 for name in MARGINAL_FIELDS}

    if terminal:
        menu, stats = menus(obs)
        selected, joint = assign(menu, int(stats["room"]), obs)
        ranked = [best_nonpass(routes) for routes in menu]
        independent = sum(routes[0].utility for routes in ranked if routes)
        top_routes = [routes[0] for routes in ranked if routes]
        conflict_pairs = sum(
            bool(left.resources & right.resources)
            for left, right in combinations(top_routes, 2)
        )
        for number in range(1, WORKER_SLOTS + 1):
            if number <= len(menu):
                _, partial = assign(menu[:number], int(stats["room"]), obs)
                marginal[f"joint_utility_first_{number}_workers"] = float(
                    partial["joint_utility"]
                )

    selected_work = [len(route.actions) for route in selected if route.actions]
    selected_units = [route_units(route) for route in selected if route.actions]
    globals_ = {
        "active_units": active_units,
        "hired_hands": len(farm["hands"]),
        "final_day": int(terminal),
        "hiring_window_open": int(terminal and obs["hour"] < 6),
        "decisions_remaining": max(0, 719 - obs["step"]),
        "shed_room": max(0, 100 - sum(obs["private"]["shed"].values())),
        "route_resources": stats.get("resources", 0),
        "routes_feasible": stats.get("routes_feasible", 0),
        "routes_retained": stats.get("routes_retained", 0),
        "assignment_leaves": joint.get("assignment_leaves", 0),
        "joint_utility": joint.get("joint_utility", 0),
        "joint_work": joint.get("joint_work", 0),
        "joint_units": joint.get("joint_units", 0),
        "independent_route_utility": independent,
        # This gap intentionally includes both resource conflicts and nonlinear shared-sale impact.
        "optimistic_coordination_gap": max(0.0, independent - joint.get("joint_utility", 0)),
        "resource_conflict_pairs": conflict_pairs,
        "active_routed_workers": len(selected_work),
        "max_assigned_work": max(selected_work, default=0),
        "min_assigned_work": min(selected_work, default=0),
        "max_assigned_units": max(selected_units, default=0),
        "min_assigned_units": min(selected_units, default=0),
    }
    for name in GLOBAL_FIELDS:
        vector.add(f"staffing.{name}", globals_[name], "staffing_coordination")

    for unit in range(WORKER_SLOTS):
        routes = ranked[unit] if unit < len(ranked) else []
        best = routes[0] if routes else None
        second = routes[1] if len(routes) > 1 else None
        values = {
            "present": int(unit < active_units),
            "menu_size": len(routes),
            "best_utility": best.utility if best else 0,
            "second_best_utility": second.utility if second else 0,
            "best_value": best.value if best else 0,
            "best_actions": len(best.actions) if best else 0,
            "best_units": route_units(best) if best else 0,
        }
        for name in WORKER_FIELDS:
            vector.add(
                f"staffing.worker{unit}.{name}",
                values[name],
                "staffing_worker_opportunity",
            )

    for name in MARGINAL_FIELDS:
        vector.add(f"staffing.{name}", marginal[name], "staffing_marginal_worker_value")

    if len(vector.values) != FEATURE_COUNT:
        raise RuntimeError("Staffing feature schema count drift")
    return vector
