"""Public, credential-free verification of study 4 and its private-audit receipts."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from kaggriculture_research.artifacts import digest, file_digest
from kaggriculture_research.market_history import BOUNDED_PRODUCTS
from kaggriculture_research.supply_experiment import KEYS, job_plan, paired_summary


def verify_supply(root: Path) -> None:
    protocol = json.loads((root / "configs/supply_research.json").read_text())
    report = json.loads((root / "reports/supply_research.json").read_text())
    registration = json.loads((root / "reports/supply_registration.json").read_text())
    common, jobs = job_plan(root, protocol)
    identity = {
        "lineage": common,
        "runner_sha256": file_digest(root / "scripts/run_supply_research.py"),
        "jobs": [{"key": j["key"], "path": j["path"]} for j in jobs],
    }
    if (
        registration["identity"] != identity
        or registration["identity_sha256"] != digest(identity)
        or registration["outcomes_inspected_before_registration"]
    ):
        raise ValueError("Source registration is stale or post-hoc")
    if report["lineage"] != common or report["protocol_sha256"] != digest(protocol):
        raise ValueError("Source/protocol lineage changed")
    if (
        report["games"] != 64
        or report["seed_clusters"] != 4
        or report["validation_or_holdout_used"]
        or report["feature_completion_gate"] != "closed"
    ):
        raise ValueError("Research scope or gate changed")
    frame = pd.read_csv(root / "reports/supply_games.csv")
    expected = {tuple(j["key"][k] for k in KEYS) for j in jobs}
    if len(frame) != 64 or set(frame[list(KEYS)].itertuples(index=False, name=None)) != expected:
        raise ValueError("Incomplete/duplicated supply experiment")
    if not np.isfinite(frame.select_dtypes(include="number").to_numpy()).all():
        raise ValueError("Non-finite outcomes")
    if not (
        frame.match_score == (frame.coin_margin > 0).astype(float) + 0.5 * (frame.coin_margin == 0)
    ).all():
        raise ValueError("Match score inconsistent with reward margin")
    if not (
        frame.harvested_units
        == frame.sold_units + frame.discarded_units + frame.unsold_product_units
    ).all():
        raise ValueError("Product conservation failed")
    if not (frame.state_roundtrips == 31).all():
        raise ValueError("Incomplete state-restoration coverage")
    effects = paired_summary(frame, protocol["bootstrap_resamples"], protocol["bootstrap_seed"])
    for published in (
        pd.DataFrame(report["effects"]),
        pd.read_csv(root / "reports/supply_effects.csv"),
    ):
        pd.testing.assert_frame_equal(
            effects, published, check_dtype=False, check_like=True, atol=1e-9, rtol=0
        )
    groups = (
        frame.groupby(["opponent", "arm"])
        .mean(numeric_only=True)
        .drop(columns=["seed", "seat"])
        .reset_index()
    )
    pd.testing.assert_frame_equal(
        groups,
        pd.DataFrame(report["groups"]),
        check_dtype=False,
        check_like=True,
        atol=1e-9,
        rtol=0,
    )
    registry = pd.read_csv(root / "reports/supply_registry.csv")
    screen = report["screening"]
    if (
        len(registry) != 1308
        or registry.feature.nunique() != 1308
        or screen["generated_features"] != 1308
        or screen["screened_features"] != 1308
    ):
        raise ValueError("Feature bank dimensions differ")
    if (
        screen["retained_for_final_model"] != 0
        or screen["rejected_for_final_model"] != 0
        or screen["sampled_development_observations"] != 64 * 181
    ):
        raise ValueError("Descriptive screen misrepresented or incomplete")
    if registry.family.value_counts().to_dict() != screen["families"]:
        raise ValueError("Feature family counts differ")
    if set(registry.loc[registry.distinct_development_values <= 1, "feature"]) != set(
        screen["constant_features"]
    ):
        raise ValueError("Constant-feature coverage differs")
    correlations = pd.read_csv(root / "reports/supply_correlations.csv")
    if (
        len(correlations) != screen["high_spearman_pairs"]
        or not correlations.spearman.abs().between(0.995 - 1e-12, 1 + 1e-12).all()
    ):
        raise ValueError("Correlation audit differs")
    audit = json.loads((root / "reports/supply_integrity.json").read_text())
    hashes = {
        "audit_code_sha256": "scripts/audit_supply_evidence.py",
        "report_sha256": "reports/supply_research.json",
        "bounds_csv_sha256": "reports/supply_bound_diagnostics.csv",
        "actions_csv_sha256": "reports/supply_action_identities.csv",
    }
    if any(audit[k] != file_digest(root / path) for k, path in hashes.items()):
        raise ValueError("Independent audit source or evidence changed")
    counts = {
        "games_verified": 64,
        "candidate_callbacks_verified": 64 * 719,
        "sampled_feature_vectors_recomputed": 64 * 181,
        "features_per_vector": 1308,
        "stock_containment_checks": 64 * 719 * 7,
        "sale_containment_checks": 64 * 718 * 7,
        "bound_violations": 0,
        "policy_action_mismatches": 0,
        "state_roundtrips": 64 * 31,
    }
    if any(audit[k] != value for k, value in counts.items()):
        raise ValueError("Independent audit incomplete or violated")
    if (
        audit["episode_manifest_sha256"] != digest(report["artifact_manifest"])
        or not audit["product_conservation_verified"]
        or audit["validation_or_holdout_used"]
    ):
        raise ValueError("Independent audit lineage or gate differs")
    manifest = {a["path"]: a for a in report["artifact_manifest"]}
    if len(manifest) != 64 or set(manifest) != {j["path"] for j in jobs}:
        raise ValueError("Episode manifest differs from registered jobs")
    cloud = json.loads((root / "reports/supply_cloud_verification.json").read_text())
    if (
        cloud["registration_sha256"] != file_digest(root / "reports/supply_registration.json")
        or cloud["compute_used"] != "local_cpu_no_additional_aws_compute"
        or cloud["verification_code_sha256"]
        != file_digest(root / "scripts/verify_supply_storage.py")
        or cloud["bucket"] != "sagemaker-kaggriculture-560403859723-us-west-2"
        or cloud["prefix"] != "runs/cash-constrained-supply-20260910/"
    ):
        raise ValueError("Execution/publication receipt changed")
    remote = {a["path"]: a for a in cloud["artifacts"]}
    if len(remote) != 75 or len(cloud["artifacts"]) != 75:
        raise ValueError("Remote evidence set incomplete or duplicated")
    if remote["artifacts/supply_source.zip"]["sha256"] != (
        "080270bfdc81285db890147b69b4cc71460a9b961231197e5b188b0d9a82f30f"
    ):
        raise ValueError("Preregistered source archive changed")
    for artifact in [*report["artifact_manifest"], screen["matrix_artifact"]]:
        if artifact["sha256"] != remote[artifact["path"]]["sha256"]:
            raise ValueError("Private artifact digest differs from verified S3 receipt")
    for item in remote.values():
        if (
            not item["version_id"]
            or item["encryption"] != "AES256"
            or not item["remote_receipt_matched"]
            or not item["remote_bytes_sha256_verified"]
        ):
            raise ValueError("Private persistence not verified")
        expected_key = (
            "releases/cash-constrained-supply/source.zip"
            if item["path"] == "artifacts/supply_source.zip"
            else cloud["prefix"] + item["path"]
        )
        if item["key"] != expected_key:
            raise ValueError("Unexpected remote evidence destination")
    for filename in (
        "supply_games.csv",
        "supply_effects.csv",
        "supply_registry.csv",
        "supply_correlations.csv",
        "supply_research.json",
        "supply_integrity.json",
        "supply_bound_diagnostics.csv",
        "supply_action_identities.csv",
        "supply_registration.json",
    ):
        relative = "reports/" + filename
        if remote[relative]["sha256"] != file_digest(root / relative):
            raise ValueError("Published result differs from verified remote bytes")
    # Recheck the post-hoc old-trace cash audit without needing private episodes in CI.
    cash = json.loads((root / "reports/cash_history_research.json").read_text())
    for field, relative in (
        ("source_report_sha256", "reports/market_research.json"),
        ("feature_code_sha256", "src/kaggriculture_research/cash_history.py"),
        ("analysis_code_sha256", "scripts/analyze_cash_history.py"),
    ):
        if cash["lineage"][field] != file_digest(root / relative):
            raise ValueError("Cash-history replay lineage changed")
    if (
        cash["games_reused"] != 48
        or cash["new_games"] != 0
        or cash["bound_violations"] != 0
        or cash["callback_vectors"] != 48 * 719
    ):
        raise ValueError("Cash-history replay coverage differs")
    bounds = pd.read_csv(root / "reports/supply_bound_diagnostics.csv")
    expected_bounds = {(*key, product) for key in expected for product in BOUNDED_PRODUCTS}
    if (
        len(bounds) != 64 * 7
        or bounds.duplicated([*KEYS, "product"]).any()
        or set(bounds[[*KEYS, "product"]].itertuples(index=False, name=None)) != expected_bounds
        or not (bounds.cash_excess <= bounds.loose_excess).all()
    ):
        raise ValueError("Bound diagnostics incomplete or inconsistent")
    if bounds.callbacks.sum() != 64 * 719 * 7:
        raise ValueError("Stock bound callback coverage differs")
    actions = pd.read_csv(root / "reports/supply_action_identities.csv")
    if (
        len(actions) != 64
        or set(actions[list(KEYS)].itertuples(index=False, name=None)) != expected
    ):
        raise ValueError("Action-identity coverage differs")


if __name__ == "__main__":
    verify_supply(Path(__file__).resolve().parents[1])
    print(
        "Verified supply study: 64 games, 1308 candidates, paired effects and independent replay."
    )
