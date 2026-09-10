"""Independently replay fixed legal traces, policies, bounds and product accounting."""

import copy
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from kaggriculture_research.artifacts import digest, file_digest, load_checkpoint, write_json
from kaggriculture_research.cash_history import own_sale_quantities
from kaggriculture_research.environment import game
from kaggriculture_research.features import PUBLIC_FIELDS, observe_features
from kaggriculture_research.market_features import market_features
from kaggriculture_research.market_history import BOUNDED_PRODUCTS
from kaggriculture_research.progress import Progress
from kaggriculture_research.relationship_features import CausalHistory, relationship_features
from kaggriculture_research.supply_experiment import job_plan, validate_episode
from kaggriculture_research.supply_policy import SupplyPolicy


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/supply_research.json").read_text())
    report = json.loads((root / "reports/supply_research.json").read_text())
    common, jobs = job_plan(root, protocol)
    if report["lineage"] != common:
        raise ValueError("Study report lineage differs from the execution source")
    manifest = {a["path"]: a for a in report["artifact_manifest"]}
    if set(manifest) != {j["path"] for j in jobs} or len(manifest) != 64:
        raise ValueError("Study manifest incomplete or duplicated")
    game_rows, bound_rows = [], []
    callbacks = samples_checked = stock_checks = sale_checks = restores = 0
    progress = Progress()
    for job in jobs:
        path = root / job["path"]
        if file_digest(path) != manifest[job["path"]]["sha256"]:
            raise ValueError("Episode byte checksum differs")
        payload = load_checkpoint(path, job["lineage"])
        if payload is None:
            raise ValueError("Episode lineage differs")
        validate_episode(payload, job["key"])
        if payload["semantic_sha256"] != manifest[job["path"]]["semantic_sha256"]:
            raise ValueError("Episode semantic identity differs from published manifest")
        records = {(r["player"], r["observation"]["step"]): r for r in payload["records"]}
        sampled = {s["step"]: s["values"] for s in payload["feature_samples"]}
        seat = job["key"]["seat"]
        policy, history, counts = SupplyPolicy(job["key"]["arm"]), CausalHistory(), Counter()
        metrics = {p: defaultdict(int) for p in BOUNDED_PRODUCTS}
        previous_sales = None
        action_trace, observation_trace = [], []
        minimum_cash = 3000
        with progress.stage("audit_supply_" + "_".join(map(str, job["key"].values()))):
            for step in range(719):
                record = records[seat, step]
                obs, action = record["observation"], record["action"]
                if set(obs) != set(PUBLIC_FIELDS):
                    raise ValueError("Unexpected trace metadata in policy observation")
                before = copy.deepcopy(obs)
                replay = policy(obs)
                if (
                    obs != before
                    or replay != action
                    or policy.last_diagnostics != record["diagnostics"]
                ):
                    raise ValueError(
                        "Policy action/diagnostics replay differs or observation mutated"
                    )
                action_trace.append(action)
                observation_trace.append(obs)
                past = history.observe(obs)
                if step in sampled:
                    # Reconstruct independently, not through experiment.feature_bank.
                    vectors = [
                        observe_features(obs),
                        relationship_features(obs),
                        past,
                        market_features(obs),
                        policy.last_features["history"],
                        policy.last_features["cash"],
                    ]
                    values = {k: v for f in vectors for k, v in f.values.items()}
                    schema = {k: v for f in vectors for k, v in f.families.items()}
                    if len(values) != 1308 or schema != payload["feature_schema"]:
                        raise ValueError("Recomputed feature schema differs")
                    np.testing.assert_allclose(
                        [values[k] for k in payload["feature_columns"]],
                        sampled[step],
                        rtol=0,
                        atol=1e-12,
                    )
                    samples_checked += 1
                minimum_cash = min(minimum_cash, obs["farms"][seat]["money"])
                farm, private = copy.deepcopy((obs["farms"][seat], obs["private"]))
                for index, command in enumerate([action["farmer"], *action["hands"]]):
                    previous = copy.deepcopy((farm, private))
                    carried = sum(private["inventories"][index].values())
                    shed = sum(private["shed"].values())
                    game._apply_unit_action(farm, private, index, command, 10, obs["day"], 24, 100)
                    if command[0] != "PASS" and previous == (farm, private):
                        counts["ineffective_farm_actions"] += 1
                    after = sum(private["inventories"][index].values())
                    if command[0] == "HARVEST":
                        counts["harvested_units"] += after - carried
                    if command[0] == "DROP":
                        counts["discarded_units"] += (
                            carried - after - (sum(private["shed"].values()) - shed)
                        )
                for order in action["market"]:
                    if order[0] == "SELL":
                        _, item, quantity = order
                        if quantity > private["shed"].get(item, 0):
                            raise ValueError("Sale exceeds own post-farm inventory")
                        counts["sold_units"] += quantity
                        private["shed"][item] -= quantity
                    elif order[0] not in ("BUY_SEED", "HIRE"):
                        raise ValueError("Crop-only accounting contract differs")
                if obs["hour"] == 23:
                    counts["discarded_units"] += max(
                        0,
                        sum(private["shed"].values())
                        + sum(sum(i.values()) for i in private["inventories"])
                        - 100,
                    )
                for name, count in record["diagnostics"]["interventions"].items():
                    counts["interventions_" + name] += count
                for name in ("supply_activations", "cash_extra_sale_units"):
                    counts[name] += record["diagnostics"][name]
                # Evaluator-only truth is inspected only AFTER policy/feature replay.
                rival = records[1 - seat, step]
                hidden = rival["observation"]["private"]
                for item, row in metrics.items():
                    actual = hidden["shed"].get(item, 0) + sum(
                        i.get(item, 0) for i in hidden["inventories"]
                    )
                    loose, tight = policy.history.upper[item], policy.cash.upper[item]
                    if not 0 <= actual <= tight <= loose:
                        raise ValueError(f"Stock containment failed: {job['key']}, {step}, {item}")
                    stock_checks += 1
                    row["callbacks"] += 1
                    row["actual_stock_positive"] += int(actual > 0)
                    row["loose_excess"] += loose - actual
                    row["cash_excess"] += tight - actual
                    row["strictly_tighter"] += int(tight < loose)
                    row["loose_false_positive"] += int(actual == 0 and loose > 0)
                    row["cash_false_positive"] += int(actual == 0 and tight > 0)
                    if step:
                        cash_row = policy.cash.base.rows[-1][item]
                        if (
                            not cash_row["sales_lower"]
                            <= previous_sales[item]
                            <= cash_row["sales_upper"]
                        ):
                            raise ValueError("Sale interval excluded actual rival sales")
                        sale_checks += 1
                        row["sale_units"] += previous_sales[item]
                        row["loose_sale_lower"] += int(policy.history.rows[-1][item]["sales_lower"])
                        row["cash_sale_lower"] += int(cash_row["sales_lower"])
                previous_sales = own_sale_quantities(rival["observation"], rival["action"])
                if step % 24 == 0 or step == 718:
                    policy = SupplyPolicy.from_state_dict(policy.state_dict())
                    restores += 1
                    counts["state_roundtrips"] += 1
                callbacks += 1
        summary = payload["summary"]
        for name in (
            "harvested_units",
            "sold_units",
            "discarded_units",
            "ineffective_farm_actions",
            "interventions_delivery",
            "interventions_market_timing",
            "supply_activations",
            "cash_extra_sale_units",
            "state_roundtrips",
        ):
            if counts[name] != summary[name]:
                raise ValueError(f"Trace accounting differs for {name}")
        if minimum_cash != summary["minimum_observed_cash"]:
            raise ValueError("Minimum observed cash differs")
        terminal = payload["evaluator_terminal_private"]
        unsold = sum(
            n
            for inv in [terminal["shed"], *terminal["inventories"]]
            for p, n in inv.items()
            if p in game.PRODUCTS
        )
        if (
            unsold != summary["unsold_product_units"]
            or counts["harvested_units"]
            != counts["sold_units"] + counts["discarded_units"] + unsold
        ):
            raise ValueError("Independent product conservation failed")
        bound_rows.extend({**job["key"], "product": p, **dict(row)} for p, row in metrics.items())
        game_rows.append(
            {
                **job["key"],
                "candidate_actions_sha256": digest(action_trace),
                "candidate_observations_sha256": digest(observation_trace),
            }
        )
    pd.DataFrame(bound_rows).to_csv(root / "reports/supply_bound_diagnostics.csv", index=False)
    pd.DataFrame(game_rows).to_csv(root / "reports/supply_action_identities.csv", index=False)
    result = {
        "games_verified": len(jobs),
        "candidate_callbacks_verified": callbacks,
        "sampled_feature_vectors_recomputed": samples_checked,
        "features_per_vector": 1308,
        "stock_containment_checks": stock_checks,
        "sale_containment_checks": sale_checks,
        "bound_violations": 0,
        "policy_action_mismatches": 0,
        "state_roundtrips": restores,
        "product_conservation_verified": True,
        "validation_or_holdout_used": False,
        "feature_completion_gate": "closed",
        "audit_code_sha256": file_digest(Path(__file__)),
        "report_sha256": file_digest(root / "reports/supply_research.json"),
        "episode_manifest_sha256": digest(report["artifact_manifest"]),
        "bounds_csv_sha256": file_digest(root / "reports/supply_bound_diagnostics.csv"),
        "actions_csv_sha256": file_digest(root / "reports/supply_action_identities.csv"),
    }
    if (callbacks, samples_checked, stock_checks, sale_checks, restores) != (
        64 * 719,
        64 * 181,
        64 * 719 * 7,
        64 * 718 * 7,
        64 * 31,
    ):
        raise ValueError("Independent audit coverage incomplete")
    write_json(root / "reports/supply_integrity.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
