"""Validate published history evidence without access to private episode data."""

import json
from itertools import product
from pathlib import Path

from kaggriculture_research.artifacts import digest, file_digest
from kaggriculture_research.market_history import BOUNDED_PRODUCTS


def verify_history(root: Path) -> dict:
    report = json.loads((root / "reports/market_history_research.json").read_text())
    source_path = root / "reports/market_research.json"
    source = json.loads(source_path.read_text())
    lineage = report["lineage"]
    checks = {
        "experiment_report_sha256": file_digest(source_path),
        "episode_manifest_sha256": digest(source["artifact_manifest"]),
        "source_experiment_lineage_sha256": digest(source["lineage"]),
        "analysis_code_sha256": file_digest(root / "scripts/analyze_market_history.py"),
        "feature_code_sha256": file_digest(root / "src/kaggriculture_research/market_history.py"),
    }
    if any(lineage[k] != v for k, v in checks.items()):
        raise ValueError("History evidence lineage differs")
    if (
        report["new_games"] != 0
        or report["games_reused"] != 48
        or report["callback_vectors"] != 48 * 719
        or report["bounds_violations"] != 0
        or report["validation_or_holdout_used"]
        or report["policy_changed"]
        or report["official_metric_change"] is not None
        or report["new_notebook_execution"]
    ):
        raise ValueError("History study boundary changed")
    for key in ("candidate_features", "screened_features", "provisional_features"):
        if report[key] != 333:
            raise ValueError("History feature count differs")
    if report["retained_features"] != 0 or report["rejected_features"] != 0:
        raise ValueError("Descriptive history screening is not final feature selection")
    registry = {r["name"]: r for r in report["registry"]}
    if len(registry) != 333 or len(report["registry"]) != 333:
        raise ValueError("History registry contains missing or repeated features")
    if digest(sorted(registry)) != lineage["feature_columns_sha256"]:
        raise ValueError("History column fingerprint differs")
    for entry in registry.values():
        if (
            entry["constant"] != (entry["minimum"] == entry["maximum"])
            or entry["minimum"] > entry["maximum"]
            or entry["decision"] != "provisional"
        ):
            raise ValueError("History screening entry differs")
    if (
        sum(r["constant"] for r in registry.values()) != report["constant_features"]
        or report["constant_features"] + report["varying_features"] != 333
    ):
        raise ValueError("History screening totals differ")
    members = set()
    for group in report["exact_nonconstant_duplicate_groups"]:
        if len(group) < 2 or len(group) != len(set(group)) or set(group) & members:
            raise ValueError("Duplicate-group structure differs")
        for name in group:
            if name not in registry or registry[name]["constant"]:
                raise ValueError("Duplicate group contains unknown or constant feature")
        if len({(registry[name]["minimum"], registry[name]["maximum"]) for name in group}) != 1:
            raise ValueError("Duplicate feature ranges disagree")
        members.update(group)
    protocol = source["lineage"]["protocol"]
    expected = set(
        product(protocol["development_seeds"], (0, 1), protocol["arms"], BOUNDED_PRODUCTS)
    )
    groups = report["groups"]
    if (
        len(groups) != len(expected)
        or {tuple(r[k] for k in ("seed", "seat", "arm", "product")) for r in groups} != expected
    ):
        raise ValueError("History development groups differ")
    fields = set(groups[0]) - {"seed", "seat", "arm", "product"}
    for row in groups:
        if (
            row["callbacks"] != 719
            or row["transitions"] != 718
            or any(type(row[k]) is not int or row[k] < 0 for k in fields)
            or row["sale_lower_units"] > row["gross_sale_units"]
            or row["gross_sale_units"] > row["sale_lower_units"] + row["sale_bound_width_sum"]
            or row["stock_bound_exact_callbacks"] > 719
            or row["sale_bounds_exact_transitions"] > 718
            or row["stored_positive_without_visible_ready_callbacks"]
            > row["stored_positive_callbacks"]
            or row["stored_positive_callbacks"] + row["empty_but_upper_positive_callbacks"]
            != row["upper_positive_callbacks"]
        ):
            raise ValueError("History group conservation/counts differ")
    totals = []
    for item in BOUNDED_PRODUCTS:
        subset = [r for r in groups if r["product"] == item]
        totals.append(
            {
                "product": item,
                **{
                    field: max(r[field] for r in subset)
                    if field.endswith("_max")
                    else sum(r[field] for r in subset)
                    for field in sorted(fields)
                },
            }
        )
    if totals != report["products"] or report["supported_stock_products"] != list(BOUNDED_PRODUCTS):
        raise ValueError("History product aggregation differs")
    if report["unsupported_stock_products"] != ["WHEAT", "FERTILIZER"]:
        raise ValueError("Unsupported-stock masks changed")
    if report["serialized_roundtrips_verified"] != 48 * 31:
        raise ValueError("Serialized history checkpoint coverage differs")
    return {"reused_games": 48, "new_games": 0, "history_features": 333, "callback_vectors": 34512}


def main() -> None:
    print(json.dumps(verify_history(Path(__file__).resolve().parents[1])))


if __name__ == "__main__":
    main()
