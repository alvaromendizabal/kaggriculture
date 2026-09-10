"""Inspect crop-only trace conservation and coverage without changing the policy.

This is a post-experiment audit, never an input to either player. It identifies
storage/disposal loss as harvested units minus requested sales minus final held
units. In this policy all sale quantities come from the legal own-farm shadow
inventory, so they are feasible. No product purchases or consumption occur.
"""

import copy
import json
from pathlib import Path

import pandas as pd

from kaggriculture_research.artifacts import file_digest, load_checkpoint, write_json
from kaggriculture_research.environment import game
from kaggriculture_research.progress import Progress


def audit(root: Path) -> None:
    report = json.loads((root / "reports/feature_research.json").read_text())
    rows = []
    progress = Progress()
    with progress.stage("post_experiment_crop_conservation"):
        for artifact in report["artifact_manifest"]:
            path = root / artifact["path"]
            if file_digest(path) != artifact["sha256"]:
                raise ValueError("Trace file differs from the experiment manifest")
            # Lineage comes from the registered report; infer episode keys from its row.
            import gzip

            envelope = json.loads(gzip.decompress(path.read_bytes()))
            summary = envelope["payload"]["summary"]
            lineage = {
                **report["lineage"],
                **{k: summary[k] for k in ("seed", "opponent", "seat", "variant")},
            }
            payload = load_checkpoint(path, lineage)
            if payload is None:
                raise ValueError("Trace lineage differs from the registered experiment")
            harvested = sold = deposit_loss = 0
            final_plants = final_yield = 0
            min_cash = 3000.0
            for record in payload["records"]:
                if record["player"] != summary["seat"]:
                    continue
                obs, action = record["observation"], record["action"]
                farm = copy.deepcopy(obs["farms"][summary["seat"]])
                private = copy.deepcopy(obs["private"])
                min_cash = min(min_cash, farm["money"])
                for idx, unit_action in enumerate([action["farmer"], *action["hands"]]):
                    before = sum(private["inventories"][idx].values())
                    shed_before = sum(private["shed"].values())
                    game._apply_unit_action(farm, private, idx, unit_action, 10, obs["day"], 24)
                    after = sum(private["inventories"][idx].values())
                    if unit_action[0] == "HARVEST":
                        harvested += after - before
                    elif unit_action[0] == "DROP":
                        deposit_loss += (
                            before - after - (sum(private["shed"].values()) - shed_before)
                        )
                for order in action["market"]:
                    if order[0] == "SELL":
                        _, item, quantity = order
                        if quantity > private["shed"].get(item, 0):
                            raise ValueError("Sale request exceeds the observable available stock")
                        private["shed"][item] -= quantity
                        sold += quantity
                    elif order[0] not in ("BUY_SEED", "HIRE"):
                        raise ValueError(
                            "Conservation audit is valid only for this crop-only policy"
                        )
                if obs["hour"] == 23:
                    stock = sum(private["shed"].values()) + sum(
                        sum(inv.values()) for inv in private["inventories"]
                    )
                    deposit_loss += max(0, stock - 100)
                if obs["step"] == 718:
                    plants = [
                        t
                        for row in farm["tiles"]
                        for t in row
                        if isinstance(t, dict) and t["kind"] == "PLANT"
                    ]
                    final_plants = len(plants)
                    final_yield = sum(t["yield_units"] for t in plants)
            residual = harvested - sold - summary["unsold_product_units"]
            if residual != deposit_loss or residual < 0:
                raise ValueError("Crop-product conservation failed")
            rows.append(
                {
                    **{k: summary[k] for k in ("seed", "seat", "variant", "opponent")},
                    "harvested_units": harvested,
                    "sold_units": sold,
                    "discarded_units": deposit_loss,
                    "minimum_observed_cash": min_cash,
                    "standing_plants_after_final_farm_actions": final_plants,
                    "standing_yield_units_after_final_farm_actions": final_yield,
                }
            )
    frame = pd.DataFrame(rows)
    frame.to_csv(root / "reports/feature_behavior.csv", index=False)
    write_json(
        root / "reports/feature_behavior_audit.json",
        {
            "audit_code_sha256": file_digest(Path(__file__)),
            "experiment_protocol_sha256": report["protocol_sha256"],
            "conservation_verified_games": len(frame),
            "group_means": frame.groupby("variant")
            .mean(numeric_only=True)
            .drop(columns=["seed", "seat"])
            .reset_index()
            .to_dict("records"),
            "standing_yield_caveat": "Includes immature crops; not liquid cash or a value forecast",
        },
    )


if __name__ == "__main__":
    audit(Path(__file__).resolve().parents[1])
