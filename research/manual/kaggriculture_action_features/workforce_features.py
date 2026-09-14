"""Forward-only workforce representation. No policy, engine, reward or replay access.

A fixed-size aggregate vector plus variable-length worker/task rows. Worker index
0 is the farmer; hired hands retain their observation/action indices. Geometry
features are independent-task opportunity bounds, not schedules or policy values.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
import math
from typing import Any

SCHEMA_VERSION = "workforce-v1"
PUBLIC_FARM = ("money", "tiles", "farmer", "hands", "unlocked_quadrants", "hires_today")
TASK_KINDS = ("harvest", "water", "feed", "care", "weed")
SHED_ACCESS = ((4, 4), (4, 5), (5, 4), (5, 5))


def integer(value: Any, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: expected an integer")
    if not math.isfinite(value) or int(value) != value or value < minimum:
        raise ValueError(f"{name}: invalid integer {value!r}")
    return int(value)


def flag(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name}: expected boolean")
    return value


def position(value: Any) -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("Expected [x, y]")
    x, y = (integer(v, "coordinate") for v in value)
    if x >= 10 or y >= 10:
        raise ValueError("Coordinates outside registered 10x10 board")
    return x, y


def counts(value: Any, name: str) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name}: expected item-count mapping")
    return {str(k): integer(v, f"{name}.{k}") for k, v in value.items()}


def canonical_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Allowlisted callback fields only; no opponent private-state lookup or hand cap.

    step=None/missing is derived from public day/hour. Conflicting non-null steps
    fail closed. A terminal state at step 719 is not a policy callback.
    """
    player = integer(observation["player"], "player")
    day = integer(observation["day"], "day")
    hour = integer(observation["hour"], "hour")
    if player not in (0, 1) or day > 29 or hour > 23:
        raise ValueError("Unexpected seat/day/hour")
    step = 24 * day + hour
    raw = observation.get("step")
    if raw is not None and integer(raw, "step") != step:
        raise ValueError("Conflicting step versus day/hour")
    if step > 718:
        raise ValueError("Outside pinned decision horizon 0..718")
    farms = observation["farms"]
    if not isinstance(farms, (list, tuple)) or len(farms) != 2:
        raise ValueError("Expected two public farms")
    projected = []
    for farm in farms:
        f = {name: farm[name] for name in PUBLIC_FARM}
        if len(f["tiles"]) != 10 or any(len(row) != 10 for row in f["tiles"]):
            raise ValueError("Expected registered 10x10 board")
        f["farmer"] = position(f["farmer"])
        f["hands"] = [position(p) for p in f["hands"]]
        f["hires_today"] = integer(f["hires_today"], "hires_today")
        if isinstance(f["money"], bool) or not isinstance(f["money"], (float, int)) or not math.isfinite(f["money"]):
            raise ValueError("Non-finite public cash")
        projected.append(f)
    private = observation["private"]
    inv = private["inventories"]
    if len(inv) != 1 + len(projected[player]["hands"]):
        raise ValueError("Own worker/inventory alignment mismatch; never truncate or pad")
    return {"player": player, "day": day, "hour": hour, "step": step,
            "farms": projected,
            "private": {"inventories": [counts(v, "inventory") for v in inv],
                        "shed": counts(private["shed"], "shed"),
                        "seeds": counts(private["seeds"], "seeds")}}


@dataclass(frozen=True)
class Rules:
    crop_first_yield: Mapping[str, int]
    animal_product: Mapping[str, str]

    @classmethod
    def from_game(cls, game: Any) -> "Rules":
        return cls({k: integer(v["first_yield_day"], "first_yield_day") for k, v in game.CROPS.items()},
                   {k: str(v["product"]) for k, v in game.ANIMALS.items()})


@dataclass
class FeatureResult:
    state: dict[str, float]
    workers: list[dict[str, Any]]
    tasks: list[dict[str, Any]]


def distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


def shed_distance(p: tuple[int, int]) -> int:
    return min(distance(p, q) for q in SHED_ACCESS)


def task_rows(farm: dict, day: int, rules: Rules) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    def add(kind: str, x: int, y: int, units: int = 0, urgent: bool = False):
        rows.append({"task_id": f"{kind}:{x}:{y}", "kind": kind, "x": x, "y": y,
                     "units": units, "urgent": int(urgent)})
    for y, line in enumerate(farm["tiles"]):
        for x, tile in enumerate(line):
            if tile is None or tile == "LOCKED":
                continue
            if not isinstance(tile, Mapping):
                raise ValueError("Unknown tile encoding")
            kind = tile["kind"]
            if kind == "PLANT":
                crop = tile["crop"]
                if crop not in rules.crop_first_yield:
                    raise ValueError(f"Unregistered crop {crop}")
                age = day - integer(tile["planted_day"], "planted_day")
                if age < 0:
                    raise ValueError("Plant comes from the future")
                units = integer(tile["yield_units"], "yield_units")
                watered = flag(tile["watered_today"], "watered_today")
                missed = integer(tile["consecutive_unwatered"], "consecutive_unwatered")
                if age >= rules.crop_first_yield[crop] and units:
                    add("harvest", x, y, units)
                if not watered:
                    add("water", x, y, urgent=missed >= 1)
            elif kind in ("COOP", "PASTURE"):
                animal = tile.get("animal")
                if animal is None:
                    continue
                if animal not in rules.animal_product:
                    raise ValueError(f"Unregistered animal {animal}")
                units = integer(tile["yield_units"], "animal yield_units")
                if units:
                    add("harvest", x, y, units)
                fed = flag(tile["fed_today"], "fed_today")
                if not fed:
                    add("feed", x, y, urgent=integer(tile["consecutive_unfed"], "consecutive_unfed") >= 1)
                if not flag(tile["cared_today"], "cared_today"):
                    add("care", x, y)
            elif kind == "WEED":
                add("weed", x, y)
            else:
                raise ValueError(f"Unregistered tile kind {kind}")
    return rows


def extract_workforce(observation: Mapping[str, Any], rules: Rules) -> FeatureResult:
    """Candidate features only. No learned weights and no actions or policy promotion.

    Reachability is tested one task at a time, ignoring conflicts and feeding
    supplies. A task counted for five workers is not five achievable completions.
    The deposit bound excludes overnight auto-drop and future market response.
    """
    obs = canonical_observation(observation)
    state: dict[str, float] = {}
    def add(name: str, value: float):
        if name in state or not math.isfinite(value):
            raise ValueError(f"Duplicate/non-finite feature {name}")
        state[name] = float(value)
    remaining = 719 - obs["step"]
    today = min(24-obs["hour"], remaining)
    add("time.remaining_decisions", remaining)
    add("time.remaining_actions_today", today)
    all_workers, all_tasks = [], []
    for label, index in (("own", obs["player"]), ("opponent", 1-obs["player"])):
        farm = obs["farms"][index]
        positions = [farm["farmer"], *farm["hands"]]
        n = len(positions)
        tasks = task_rows(farm, obs["day"], rules)
        prefix = label + "."
        add(prefix+"worker_count", n)
        add(prefix+"hired_hands", n-1)
        add(prefix+"worker_action_budget_today", n*today)
        add(prefix+"distinct_worker_positions", len(set(positions)))
        add(prefix+"colocated_worker_pairs", sum(v*(v-1)/2 for v in Counter(positions).values()))
        add(prefix+"shed_distance_mean", sum(shed_distance(p) for p in positions)/n)
        add(prefix+"shed_distance_max", max(shed_distance(p) for p in positions))
        add(prefix+"workers_at_shed", sum(shed_distance(p)==0 for p in positions))
        add(prefix+"public_cash", farm["money"])
        add(prefix+"task_count", len(tasks))
        add(prefix+"task_actions_per_available_worker_action", len(tasks)/(n*today))
        worker_rows = [{"side": label, "worker_index": i, "is_farmer": int(i==0),
                        "x": p[0], "y": p[1], "shed_distance": shed_distance(p),
                        "available_actions_today": today,
                        "inventory_observed": int(label=="own"),
                        "carried_units": sum(obs["private"]["inventories"][i].values()) if label=="own" else None}
                       for i, p in enumerate(positions)]
        for kind in TASK_KINDS:
            group = [t for t in tasks if t["kind"]==kind]
            for row, p in zip(worker_rows, positions, strict=True):
                costs = sorted(distance(p, (t["x"], t["y"]))+1 for t in group)
                row[kind+"_present"] = int(bool(costs))
                row[kind+"_best_actions"] = costs[0] if costs else 0
                row[kind+"_second_present"] = int(len(costs)>1)
                row[kind+"_second_actions"] = costs[1] if len(costs)>1 else 0
                row[kind+"_alternative_gap"] = costs[1]-costs[0] if len(costs)>1 else 0
                row[kind+"_independent_reachable_today"] = sum(c<=today for c in costs)
            nearest, access, gaps = [], [], []
            for t in group:
                costs = sorted(distance(p, (t["x"], t["y"]))+1 for p in positions)
                nearest.append(costs[0]); access.append(sum(c<=today for c in costs))
                gaps.append(costs[1]-costs[0] if len(costs)>1 else 0)
                t.update({"side":label,"nearest_worker_actions":costs[0],
                          "second_worker_present":int(len(costs)>1),
                          "second_worker_actions":costs[1] if len(costs)>1 else 0,
                          "independent_eligible_workers_today":access[-1],
                          "nearest_worker_ties":sum(c==costs[0] for c in costs),
                          "best_worker_loss_distance_gap":gaps[-1],
                          "manual_cash_actions_lower_bound":costs[0]+shed_distance((t["x"],t["y"]))+1 if kind=="harvest" else None})
            stem = prefix+kind+"."
            add(stem+"count", len(group)); add(stem+"urgent_count", sum(t["urgent"] for t in group))
            add(stem+"nearest_actions_mean", sum(nearest)/len(nearest) if nearest else 0)
            add(stem+"nearest_actions_max", max(nearest, default=0))
            add(stem+"independent_unreachable_today", sum(a==0 for a in access))
            add(stem+"unique_worker_access", sum(a==1 for a in access))
            add(stem+"multiple_worker_access", sum(a>1 for a in access))
            add(stem+"best_worker_loss_distance_gap_mean", sum(gaps)/len(gaps) if gaps else 0)
        harvest = [t for t in tasks if t["kind"]=="harvest"]
        add(prefix+"harvest.visible_units", sum(t["units"] for t in harvest))
        add(prefix+"harvest.manual_cash_reachable_units_bound", sum(t["units"] for t in harvest if t["manual_cash_actions_lower_bound"] <= today))
        add(prefix+"harvest.manual_cash_unreachable_units_bound", sum(t["units"] for t in harvest if t["manual_cash_actions_lower_bound"] > today))
        all_workers.extend(worker_rows); all_tasks.extend(tasks)
    for field in ("worker_count", "worker_action_budget_today", "task_count", "harvest.visible_units",
                  "harvest.manual_cash_reachable_units_bound", "shed_distance_mean"):
        add("relative."+field, state["own."+field]-state["opponent."+field])
    inventory = obs["private"]
    loads = [sum(i.values()) for i in inventory["inventories"]]
    shed_used = sum(inventory["shed"].values())
    add("own_inventory.shed_used", shed_used)
    add("own_inventory.shed_room", max(0,100-shed_used))
    add("own_inventory.carried_units", sum(loads))
    add("own_inventory.loaded_workers", sum(v>0 for v in loads))
    add("own_inventory.max_worker_load", max(loads))
    add("own_inventory.deposit_overflow_if_all_arrive", max(0,shed_used+sum(loads)-100))
    add("own_inventory.wheat_in_shed", inventory["shed"].get("WHEAT",0))
    add("own_inventory.wheat_carried", sum(i.get("WHEAT",0) for i in inventory["inventories"]))
    return FeatureResult(state, all_workers, all_tasks)
