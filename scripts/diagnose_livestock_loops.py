"""Descriptive species-level care conversion and exact product balances.

This post-registration diagnostic does not alter the registered contrasts or
select a policy. It explains resource pathways in saved development episodes.
"""

import copy
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from kaggriculture_livestock.experiment import job_plan, validate_episode
from kaggriculture_livestock.features import located
from kaggriculture_research.artifacts import digest, file_digest, load_checkpoint, write_json
from kaggriculture_research.environment import game
from kaggriculture_research.progress import Progress


def describe(payload: dict) -> tuple[list[dict], list[dict]]:
    seat = payload["summary"]["seat"]
    species = {a: Counter() for a in game.ANIMALS}
    fields = (
        "animal_nights",
        "fed_nights",
        "care_actions_flagged",
        "care_bank_additions",
        "care_without_feed",
        "production_events",
        "production_units",
        "care_units_realized",
        "care_bank_lost_unfed",
        "care_units_lost_capacity",
        "escaped_animals",
        "missed_manure_slots",
    )
    for record in payload["records"]:
        obs, action = record["observation"], record["action"]
        if record["player"] != seat or obs["hour"] != 23:
            continue
        farm, private = copy.deepcopy((obs["farms"][seat], obs["private"]))
        for index, command in enumerate([action["farmer"], *action["hands"]]):
            game._apply_unit_action(farm, private, index, command, 10, obs["day"], 24, 100)
        for _, _, tile in located(farm):
            if not tile.get("animal"):
                continue
            counts, params = species[tile["animal"]], game.ANIMALS[tile["animal"]]
            fed, cared = tile["fed_today"], tile["cared_today"]
            escape = not fed and tile["consecutive_unfed"] >= 1
            counts["animal_nights"] += 1
            counts["fed_nights"] += int(fed)
            counts["care_actions_flagged"] += int(cared)
            counts["care_bank_additions"] += int(fed and cared and not escape)
            counts["care_without_feed"] += int(cared and not fed)
            counts["escaped_animals"] += int(escape)
            if escape:
                continue
            counts["missed_manure_slots"] += int(tile["fertilizer_available"])
            age = obs["day"] + 1 - tile["placed_day"]
            due = (
                age >= params["first_yield_day"]
                and (age - params["first_yield_day"]) % params["interval"] == 0
            )
            if due:
                bank = tile["pending_care_bonus"]
                space = max(0, params["max_held"] - tile["yield_units"])
                units = min(space, 1 + (bank if fed else 0))
                bonus = max(0, units - min(space, 1))
                counts["production_events"] += 1
                counts["production_units"] += units
                counts["care_units_realized"] += bonus
                counts["care_bank_lost_unfed"] += bank if not fed else 0
                counts["care_units_lost_capacity"] += bank - bonus if fed else 0
    rows = [{"species": a, **{f: c[f] for f in fields}} for a, c in species.items()]
    products = []
    for item, counts in payload["accounting"]["products"][seat].items():
        fields = (
            "initial",
            "harvested",
            "collected",
            "bought",
            "sold",
            "fed",
            "applied",
            "discarded",
            "terminal",
        )
        row = {f: counts.get(f, 0) for f in fields}
        if row["initial"] + row["harvested"] + row["collected"] + row["bought"] != sum(
            row[k] for k in ("sold", "fed", "applied", "discarded", "terminal")
        ):
            raise ValueError("Species diagnostic received unbalanced product accounting")
        products.append({"product": item, **row})
    return rows, products


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/livestock_research.json").read_text())
    common, jobs = job_plan(root, protocol)
    species, products = [], []
    with Progress().stage("livestock_species_and_product_diagnostics"):
        for job in jobs:
            payload = load_checkpoint(root / job["path"], job["lineage"])
            if payload is None:
                raise ValueError("Complete registered study required")
            validate_episode(payload, job["key"])
            rows, balances = describe(payload)
            species.extend({**job["key"], **r} for r in rows)
            products.extend({**job["key"], **r} for r in balances)
    pd.DataFrame(species).to_csv(root / "reports/livestock_species.csv", index=False)
    pd.DataFrame(products).to_csv(root / "reports/livestock_products.csv", index=False)
    result = {
        "games": len(jobs),
        "species_rows": len(species),
        "product_rows": len(products),
        "scope": "post-registration descriptive mechanism diagnostics; no new policy selection",
        "study_sha256": digest(common),
        "analysis_source_sha256": file_digest(Path(__file__)),
        "species_sha256": file_digest(root / "reports/livestock_species.csv"),
        "products_sha256": file_digest(root / "reports/livestock_products.csv"),
    }
    write_json(root / "reports/livestock_mechanisms.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
