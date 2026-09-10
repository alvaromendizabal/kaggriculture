"""Post-game accounting; both private views are evaluator-only inputs.

Replay recorded farm commands and the official simultaneous market phase, then
compare the next real observation. Policies/features never receive this module.
"""

import copy
from collections import Counter
from types import SimpleNamespace

from kaggle_environments.utils import structify

from kaggriculture_livestock.features import product_totals
from kaggriculture_research.environment import game


def accounting(payload: dict) -> dict:
    by_player = [[r for r in payload["records"] if r["player"] == p] for p in (0, 1)]
    totals = [Counter(), Counter()]
    per_product = [{item: Counter() for item in game.PRODUCTS} for _ in (0, 1)]
    transitions = 0
    for step in range(719):
        records = [by_player[p][step] for p in (0, 1)]
        states = structify(
            [
                {"observation": copy.deepcopy(r["observation"]), "action": r["action"]}
                for r in records
            ]
        )
        farms = states[0].observation.farms
        for player in (0, 1):
            obs = states[player].observation
            obs.farms = farms
            farm, private = farms[player], obs.private
            action = states[player].action
            commands = [action["farmer"], *action["hands"]]
            demand = Counter(a[1] for a in commands if a[0] == "PLANT")
            if any(n > private["seeds"].get(k, 0) for k, n in demand.items()):
                raise ValueError("Atomic plant requests would be blocked")
            for index, command in enumerate(commands):
                before = product_totals(private)
                previous = copy.deepcopy((farm, private))
                game._apply_unit_action(farm, private, index, command, 10, obs.day, 24, 100)
                after = product_totals(private)
                changed = previous != (farm, private)
                totals[player]["ineffective_farm_actions"] += int(
                    command[0] != "PASS" and not changed
                )
                totals[player]["commands_" + command[0]] += int(changed)
                for item in game.PRODUCTS:
                    delta = after[item] - before[item]
                    if delta > 0:
                        if command[0] not in ("HARVEST", "COLLECT_FERTILIZER"):
                            raise ValueError("Unexplained farm product inflow")
                        name = "harvested" if command[0] == "HARVEST" else "collected"
                        per_product[player][item][name] += delta
                    elif delta < 0:
                        if command[0] not in ("FEED", "FERTILIZE", "DROP"):
                            raise ValueError("Unexplained farm product outflow")
                        name = {"FEED": "fed", "FERTILIZE": "applied", "DROP": "discarded"}[
                            command[0]
                        ]
                        per_product[player][item][name] -= delta
        before_market = [product_totals(s.observation.private) for s in states]
        game._process_market(states, SimpleNamespace(configuration={"episodeSteps": 720}))
        for player, state in enumerate(states):
            private = state.observation.private
            for item, value in product_totals(private).items():
                delta = value - before_market[player][item]
                # Registered policies never buy and sell one item in the same turn.
                directions = {o[0] for o in state.action["market"] if len(o) > 2 and o[1] == item}
                if {"BUY_PRODUCT", "SELL"} <= directions:
                    raise ValueError("Gross-flow accounting contract does not cover round trips")
                if delta > 0 and item not in ("WHEAT", "FERTILIZER"):
                    raise ValueError("Nonbuyable market inflow")
                per_product[player][item]["bought" if delta > 0 else "sold"] += abs(delta)
            if step % 24 == 23:
                before_night = product_totals(private)
                for row in farms[player]["tiles"]:
                    for tile in row:
                        if isinstance(tile, dict) and tile.get("animal"):
                            escape = not tile["fed_today"] and tile["consecutive_unfed"] >= 1
                            totals[player]["escaped_animals"] += int(escape)
                            totals[player]["uncollected_manure_slots"] += int(
                                not escape and tile["fertilizer_available"]
                            )
                            p = game.ANIMALS[tile["animal"]]
                            age = step // 24 + 1 - tile["placed_day"]
                            due = (
                                age >= p["first_yield_day"]
                                and (age - p["first_yield_day"]) % p["interval"] == 0
                            )
                            if not escape and due:
                                bonus = tile["pending_care_bonus"] if tile["fed_today"] else 0
                                totals[player]["overflow_production_units"] += max(
                                    0, tile["yield_units"] + 1 + bonus - p["max_held"]
                                )
                                totals[player]["lost_unfed_bonus_units"] += (
                                    0 if tile["fed_today"] else tile["pending_care_bonus"]
                                )
                game._drop_inventories_to_shed(private, 100)
                private["inventories"] = [{}]
                for item, value in product_totals(private).items():
                    per_product[player][item]["discarded"] += before_night[item] - value
            expected = (
                by_player[player][step + 1]["observation"]
                if step < 718
                else payload["evaluator_terminal_observations"][player]
            )
            if (
                private != expected["private"]
                or farms[player]["money"] != expected["farms"][player]["money"]
            ):
                raise ValueError(f"Accounting disagrees with transition {step}, player {player}")
            transitions += 1
    for player in (0, 1):
        initial = product_totals(by_player[player][0]["observation"]["private"])
        terminal = product_totals(payload["evaluator_terminal_observations"][player]["private"])
        for item, counts in per_product[player].items():
            counts["initial"], counts["terminal"] = initial[item], terminal[item]
            inflow = (
                counts["initial"] + counts["harvested"] + counts["collected"] + counts["bought"]
            )
            outflow = (
                counts["sold"]
                + counts["fed"]
                + counts["applied"]
                + counts["discarded"]
                + counts["terminal"]
            )
            if inflow != outflow:
                raise ValueError("Product-specific conservation failure")
        for name in (
            "harvested",
            "collected",
            "bought",
            "sold",
            "fed",
            "applied",
            "discarded",
            "terminal",
        ):
            totals[player][name + "_units"] = sum(c[name] for c in per_product[player].values())
    return {
        "transitions": transitions,
        "players": [dict(c) for c in totals],
        "products": per_product,
    }
