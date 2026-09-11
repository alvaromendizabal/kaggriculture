"""Deterministic correctness tests; no full games or mocked deployment timings."""

import itertools
import random
from dataclasses import dataclass

import pytest

from kaggriculture_runtime.routing import exact_assignment, revenue_curve


def price(item, inventory):
    return max(1, (20 if item == "A" else 10) - inventory)


def reference_sale(item, inventory, count):
    total = 0.0
    for _ in range(count):
        p = price(item, inventory)
        total += p
        inventory += int(p > 1)
    return total


@pytest.mark.parametrize("inventory", [-15, 0, 9, 19, 20, 100])
@pytest.mark.parametrize("maximum", [0, 1, 7, 100])
def test_all_prefixes_match_independent_sales(inventory, maximum):
    for item in ("A", "B"):
        assert revenue_curve(item, inventory, maximum, price) == [
            reference_sale(item, inventory, q) for q in range(maximum + 1)
        ]


def test_linear_work_and_floor_inventory():
    seen = []

    def floor(item, inventory):
        seen.append(inventory)
        return 1

    assert revenue_curve("A", 20, 100, floor) == list(range(101))
    assert seen == [20] * 100
    with pytest.raises(ValueError):
        revenue_curve("A", 0, -1, price)


@dataclass(frozen=True)
class Route:
    resources: frozenset
    actions: tuple
    quantities: tuple


@pytest.mark.parametrize("seed", range(12))
def test_assignment_matches_independent_exhaustive_reference(seed):
    rng = random.Random(seed)
    items, prices, room, work_value = ("A", "B"), {"A": 4, "B": 2}, 7, 2.0
    menu = []
    for _ in range(4):
        routes = [
            Route(frozenset({rng.randrange(5)}), (("MOVE",),) * rng.randrange(1, 4),
                  (rng.randrange(4), rng.randrange(4))) for _ in range(3)
        ]
        routes.append(Route(frozenset(), (), (0, 0)))
        menu.append(routes)
    best, key, leaves = None, None, 0
    for choices in itertools.product(*menu):
        used = set()
        if any(used.intersection(r.resources) or used.update(r.resources) for r in choices):
            continue
        quantities = tuple(sum(r.quantities[i] for r in choices) for i in range(2))
        if sum(quantities) > room:
            continue
        leaves += 1
        work = sum(len(r.actions) for r in choices)
        value = sum(reference_sale(i, prices[i], q) for i, q in zip(items, quantities, strict=True))
        candidate_key = (value - work_value * work, -work)
        if key is None or candidate_key > key:
            best, key = list(choices), candidate_key
    chosen, stats = exact_assignment(menu, room, prices, items, work_value, price)
    assert chosen == best
    assert stats == {"assignment_leaves": leaves, "joint_utility": key[0],
                     "joint_work": -key[1],
                     "joint_units": sum(sum(r.quantities) for r in best)}
