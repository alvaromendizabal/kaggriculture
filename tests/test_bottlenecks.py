"""Independent small-menu checks of exact decision-bottleneck descriptors."""

import copy
from dataclasses import dataclass
from itertools import product

import pytest

from kaggriculture_runtime.bottlenecks import assignment_bottlenecks


@dataclass(frozen=True)
class Route:
    resources: frozenset
    actions: tuple
    quantities: tuple


def route(resource=None, quantity=0, work=0):
    return Route(frozenset([resource]) if resource else frozenset(), ("MOVE",) * work, (quantity,))


def features(menu, room=100):
    return assignment_bottlenecks(menu, room, {"MILK": 0}, ("MILK",), lambda _, n: max(1, 10-n))


def test_zero_work_and_capacity_counterfactuals():
    menu = [[route("cow", 5, 1), route()]]
    got = features(menu, 5)
    assert got["bottleneck.best_utility"] == 32
    assert got["bottleneck.worker0_removal_loss"] == 32
    assert got["bottleneck.resource_loss_max"] == 32
    assert got["bottleneck.capacity_minus1_utility_delta"] == -32
    assert got["bottleneck.capacity_plus1_utility_delta"] == 0
    assert got["bottleneck.capacity_plus10_actual_units"] == 10
    assert len(got) == 39


def test_shared_resource_prevents_double_collection():
    got = features([[route("cow", 5, 1), route()], [route("cow", 5, 1), route()]])
    assert got["bottleneck.best_utility"] == 32
    assert got["bottleneck.optimal_plan_count"] == 2
    assert got["bottleneck.runner_up_utility_gap"] == 0
    assert got["bottleneck.worker0_removal_loss"] == 0
    assert got["bottleneck.worker1_removal_loss"] == 0
    assert got["bottleneck.resource_loss_max"] == 32


def test_hypothetical_capacity_gain_is_over_the_same_menu():
    got = features([[route("a", 3, 1), route()], [route("b", 3, 1), route()]], 3)
    assert got["bottleneck.best_utility"] == 19
    assert got["bottleneck.capacity_plus5_utility_delta"] == 10


def test_input_not_mutated_and_absent_worker_has_no_cost():
    menu = [[route("a", 3, 1), route()]]
    before = copy.deepcopy(menu)
    got = features(menu)
    assert menu == before
    assert got["bottleneck.worker3_present"] == 0
    assert got["bottleneck.worker3_removal_loss"] == 0


@pytest.mark.parametrize("room", [-1, 101, 1.5, "5"])
def test_invalid_capacity_rejected(room):
    with pytest.raises(ValueError):
        features([[route()]], room)


def test_missing_pass_and_bad_quantities_rejected():
    with pytest.raises(ValueError, match="PASS"):
        features([[route("cow", 1, 1)]])
    with pytest.raises(ValueError, match="quantities"):
        features([[route("cow", -1, 1), route()]])


@pytest.mark.parametrize("room", [0, 1, 3, 6, 10, 100])
@pytest.mark.parametrize("workers", [1, 2, 3, 4])
def test_against_independent_direct_objective(room, workers):
    menu = [[route(f"task{i}", i+1, 1), route("shared", 2, 1), route()] for i in range(workers)]
    scored = []
    for choices in product(*menu):
        all_resources = [resource for r in choices for resource in r.resources]
        amount = sum(sum(r.quantities) for r in choices)
        if amount > room or len(all_resources) != len(set(all_resources)):
            continue
        inventory = 0
        revenue = 0
        for _ in range(amount):
            p = max(1, 10-inventory)
            revenue += p
            inventory += int(p > 1)
        scored.append((revenue - 8*sum(len(r.actions) for r in choices), -sum(len(r.actions) for r in choices)))
    got = features(menu, room)
    assert got["bottleneck.best_utility"] == max(scored)[0]
    assert got["bottleneck.best_work"] == -max(scored)[1]
    assert got["bottleneck.feasible_plans"] == len(scored)
    for delta in (1, 5, 10):
        assert got[f"bottleneck.capacity_minus{delta}_utility_delta"] <= 0
        assert got[f"bottleneck.capacity_plus{delta}_utility_delta"] >= 0
