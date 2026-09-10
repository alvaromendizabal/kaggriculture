"""Recompute features and product conservation from all private study-2 traces.

Runs after download/checksum verification. It does not run new games, fit a model,
change the policy, or require validation/holdout data. Public output is aggregate.
"""

import copy
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

from kaggriculture_research.artifacts import digest, file_digest, load_checkpoint, write_json
from kaggriculture_research.environment import game
from kaggriculture_research.features import PUBLIC_FIELDS, observe_features
from kaggriculture_research.progress import Progress
from kaggriculture_research.relationship_experiment import episode_hash
from kaggriculture_research.relationship_features import CausalHistory, relationship_features


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    report = json.loads((root / "reports/relationship_research.json").read_text())
    games = rows = regenerated = 0
    sale_rows = []
    progress = Progress()
    with progress.stage("recompute_private_relationship_evidence"):
        for artifact in report["artifact_manifest"]:
            path = root / artifact["path"]
            if file_digest(path) != artifact["sha256"]:
                raise ValueError("Downloaded episode checksum differs")
            with gzip.open(path, "rt") as stream:
                summary = json.load(stream)["payload"]["summary"]
            lineage = {**report["lineage"], **{k: summary[k] for k in ("seed", "seat", "arm")}}
            payload = load_checkpoint(path, lineage)
            if payload is None or episode_hash(payload) != artifact["semantic_sha256"]:
                raise ValueError("Episode lineage or semantic identity differs")
            seat = summary["seat"]
            steps = []
            history = CausalHistory()
            first_sales = {0: {}, 1: {}}
            sale_units = {0: {}, 1: {}}
            samples = {s["step"]: s["values"] for s in payload["feature_samples"]}
            harvested = sold = discarded = ineffective = 0
            for record in payload["records"]:
                who = record["player"]
                for order in record["action"]["market"]:
                    if order[0] == "SELL" and order[2] > 0:
                        item = order[1]
                        first_sales[who].setdefault(item, record["observation"]["step"])
                        sale_units[who][item] = sale_units[who].get(item, 0) + order[2]
                if record["player"] != seat:
                    continue
                obs, action = record["observation"], record["action"]
                if set(obs) != set(PUBLIC_FIELDS):
                    raise ValueError("Trace observation includes non-contract metadata")
                steps.append(obs["step"])
                past = history.observe(obs)
                if obs["step"] in samples:
                    vectors = [observe_features(obs), relationship_features(obs), past]
                    values = {k: v for vector in vectors for k, v in vector.values.items()}
                    actual = [values[k] for k in payload["feature_columns"]]
                    np.testing.assert_allclose(actual, samples[obs["step"]], rtol=0, atol=1e-12)
                    regenerated += 1
                farm = copy.deepcopy(obs["farms"][seat])
                private = copy.deepcopy(obs["private"])
                for index, command in enumerate([action["farmer"], *action["hands"]]):
                    before = copy.deepcopy((farm, private))
                    carried_before = sum(private["inventories"][index].values())
                    shed_before = sum(private["shed"].values())
                    game._apply_unit_action(farm, private, index, command, 10, obs["day"], 24, 100)
                    if command[0] != "PASS" and before == (farm, private):
                        ineffective += 1
                    carried_after = sum(private["inventories"][index].values())
                    if command[0] == "HARVEST":
                        harvested += carried_after - carried_before
                    if command[0] == "DROP":
                        discarded += (
                            carried_before
                            - carried_after
                            - (sum(private["shed"].values()) - shed_before)
                        )
                for order in action["market"]:
                    if order[0] == "SELL":
                        _, item, quantity = order
                        if quantity > private["shed"].get(item, 0):
                            raise ValueError("Published sale exceeds available own inventory")
                        private["shed"][item] -= quantity
                        sold += quantity
                    elif order[0] not in ("HIRE", "BUY_SEED"):
                        raise ValueError("Crop conservation scope changed")
                if obs["hour"] == 23:
                    discarded += max(
                        0,
                        sum(private["shed"].values())
                        + sum(sum(i.values()) for i in private["inventories"])
                        - 100,
                    )
                rows += 1
            if steps != list(range(719)) or len(samples) != 181:
                raise ValueError("Episode or sampled-feature coverage is incomplete")
            for name, actual in (
                ("harvested_units", harvested),
                ("sold_units", sold),
                ("discarded_units", discarded),
                ("ineffective_farm_actions", ineffective),
            ):
                if actual != summary[name]:
                    raise ValueError(f"Independent trace audit differs for {name}")
            if harvested != sold + discarded + summary["unsold_product_units"]:
                raise ValueError("Recomputed product conservation failed")
            for item in game.CROPS:
                candidate_first = first_sales[seat].get(item)
                opponent_first = first_sales[1 - seat].get(item)
                sale_rows.append(
                    {
                        "seed": summary["seed"],
                        "seat": seat,
                        "arm": summary["arm"],
                        "product": item,
                        "candidate_units_sold": sale_units[seat].get(item, 0),
                        "opponent_units_sold": sale_units[1 - seat].get(item, 0),
                        "candidate_first_sale_step": candidate_first,
                        "opponent_first_sale_step": opponent_first,
                        "candidate_first_sale_lead_actions": opponent_first - candidate_first
                        if candidate_first is not None and opponent_first is not None
                        else None,
                    }
                )
            games += 1
    if (
        games != report["games"]
        or regenerated != report["screening"]["sampled_development_observations"]
    ):
        raise ValueError("Aggregate evidence count differs")
    behavior_path = root / "reports/relationship_behavior.csv"
    pd.DataFrame(sale_rows).to_csv(behavior_path, index=False)
    result = {
        "games_verified": games,
        "candidate_callback_observations_verified": rows,
        "sampled_feature_vectors_recomputed": regenerated,
        "features_per_vector": 618,
        "numerical_tolerance": {"relative": 0, "absolute": 1e-12},
        "product_conservation_verified": True,
        "validation_or_holdout_used": False,
        "audit_code_sha256": file_digest(Path(__file__)),
        "experiment_report_sha256": file_digest(root / "reports/relationship_research.json"),
        "episode_manifest_sha256": digest(report["artifact_manifest"]),
        "behavior_csv_sha256": file_digest(behavior_path),
        "behavior_scope": (
            "Post-hoc descriptive first-sale timing and crop quantities, not an "
            "additional confirmatory test or a new policy-selection dataset"
        ),
    }
    write_json(root / "reports/relationship_integrity.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
