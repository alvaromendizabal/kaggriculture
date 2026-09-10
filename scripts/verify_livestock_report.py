"""Credential-free checks of registered outcomes, accounting and saved evidence."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from kaggriculture_livestock.experiment import KEYS, job_plan, paired_summary
from kaggriculture_research.artifacts import digest, file_digest


def verify(root: Path, require_cloud: bool = True) -> None:
    protocol = json.loads((root / "configs/livestock_research.json").read_text())
    report = json.loads((root / "reports/livestock_research.json").read_text())
    registration = json.loads((root / "reports/livestock_registration.json").read_text())
    common, jobs = job_plan(root, protocol)
    identity = {
        "lineage": common,
        "runner_sha256": file_digest(root / "scripts/run_livestock_research.py"),
        "jobs": [{"key": j["key"], "path": j["path"]} for j in jobs],
    }
    if (
        registration["identity"] != identity
        or registration["identity_sha256"] != digest(identity)
        or registration["outcomes_inspected_before_registration"]
    ):
        raise ValueError("Source/protocol registration changed")
    if report["lineage"] != common or report["protocol_sha256"] != digest(protocol):
        raise ValueError("Report lineage changed")
    if report["reporting_adapter_sha256"] != file_digest(root / "scripts/summarize_livestock.py"):
        raise ValueError("Reporting adapter changed")
    if (
        report["games"] != 64
        or report["seed_clusters"] != 4
        or report["validation_or_holdout_used"]
        or report["feature_completion_gate"] != "closed"
    ):
        raise ValueError("Research scope changed")
    frame = pd.read_csv(root / "reports/livestock_games.csv")
    expected = {tuple(j["key"][k] for k in KEYS) for j in jobs}
    if len(frame) != 64 or set(frame[list(KEYS)].itertuples(index=False, name=None)) != expected:
        raise ValueError("Incomplete or duplicate games")
    if not np.isfinite(frame.select_dtypes(include="number").to_numpy()).all():
        raise ValueError("Nonfinite outcomes or telemetry")
    if not (
        frame.match_score == (frame.coin_margin > 0).astype(float) + 0.5 * (frame.coin_margin == 0)
    ).all():
        raise ValueError("Match score inconsistent")
    if not (
        frame.harvested_units + frame.collected_units + frame.bought_units
        == frame.sold_units
        + frame.fed_units
        + frame.applied_units
        + frame.discarded_units
        + frame.terminal_units
    ).all():
        raise ValueError("Mixed-farm product conservation failed")
    if not (frame.state_roundtrips == 31).all():
        raise ValueError("State-restoration coverage incomplete")
    effects = paired_summary(frame, protocol["bootstrap_resamples"], protocol["bootstrap_seed"])
    for published in (
        pd.DataFrame(report["effects"]),
        pd.read_csv(root / "reports/livestock_effects.csv"),
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
    registry = pd.read_csv(root / "reports/livestock_registry.csv")
    screen = report["screening"]
    if (
        len(registry) != 1500
        or registry.feature.nunique() != 1500
        or screen["generated_features"] != 1500
        or screen["screened_features"] != 1500
    ):
        raise ValueError("Feature schema dimensions changed")
    if (
        registry.feature.str.startswith("cash_history.").any()
        or registry.feature.str.startswith("livestock.").sum() != 234
    ):
        raise ValueError("Unsupported feature contract entered the bank")
    if (
        screen["retained_for_final_model"] != 0
        or screen["rejected_for_final_model"] != 0
        or screen["sampled_development_observations"] != 64 * 181
    ):
        raise ValueError("Descriptive screen misrepresented")
    if registry.family.value_counts().to_dict() != screen["families"]:
        raise ValueError("Family counts differ")
    if set(registry.loc[registry.distinct_development_values <= 1, "feature"]) != set(
        screen["constant_features"]
    ):
        raise ValueError("Constant coverage differs")
    correlations = pd.read_csv(root / "reports/livestock_correlations.csv")
    if (
        len(correlations) != screen["high_spearman_pairs"]
        or not correlations.spearman.abs().between(0.995 - 1e-12, 1 + 1e-12).all()
    ):
        raise ValueError("Correlation evidence differs")
    audit = json.loads((root / "reports/livestock_integrity.json").read_text())
    required = {
        "callbacks": 64 * 719,
        "feature_vectors": 64 * 181,
        "state_restores": 64 * 31,
        "stock_checks": 64 * 719 * 7,
        "sale_checks": 64 * 718 * 7,
        "private_transitions": 64 * 1438,
        "product_balances": 64 * 18,
    }
    if (
        audit["counts"] != required
        or audit["games_audited"] != 64
        or not audit["complete"]
        or audit["mismatches"] != 0
        or audit["study_sha256"] != digest(common)
        or audit["audit_code_sha256"] != file_digest(root / "scripts/audit_livestock_evidence.py")
    ):
        raise ValueError("Independent audit is incomplete or stale")
    actions = pd.read_csv(root / "reports/livestock_action_identities.csv")
    if (
        len(actions) != 64
        or set(actions[list(KEYS)].itertuples(index=False, name=None)) != expected
    ):
        raise ValueError("Action-identity coverage differs")
    manifests = report["artifact_manifest"]
    if len(manifests) != 64 or {a["path"] for a in manifests} != {j["path"] for j in jobs}:
        raise ValueError("Episode manifest differs")
    if require_cloud:
        from verify_livestock_storage import required_paths

        cloud = json.loads((root / "reports/livestock_cloud_verification.json").read_text())
        remote = {a["path"]: a for a in cloud["artifacts"]}
        if (
            set(remote) != required_paths(root)
            or cloud["bucket"] != "sagemaker-kaggriculture-560403859723-us-west-2"
            or cloud["prefix"] != "runs/livestock-resource-loops-20260910/"
            or cloud["download_verifier_sha256"]
            != file_digest(root / "scripts/verify_supply_storage.py")
        ):
            raise ValueError("Storage receipt set, destination or verifier changed")
        if (
            len(remote) != len(cloud["artifacts"])
            or cloud["registration_sha256"]
            != file_digest(root / "reports/livestock_registration.json")
            or cloud["verification_code_sha256"]
            != file_digest(root / "scripts/verify_livestock_storage.py")
        ):
            raise ValueError("Storage receipt lineage differs")
        for artifact in [*manifests, screen["matrix_artifact"]]:
            if artifact["sha256"] != remote[artifact["path"]]["sha256"]:
                raise ValueError("Private artifact differs from remote receipt")
        for item in remote.values():
            if (
                not item["version_id"]
                or item["encryption"] != "AES256"
                or not item["remote_bytes_sha256_verified"]
                or not item["remote_receipt_matched"]
            ):
                raise ValueError("Unverified remote persistence")
            if (
                item["path"].startswith("reports/")
                and file_digest(root / item["path"]) != item["sha256"]
            ):
                raise ValueError("Published result differs from saved remote bytes")
        if (
            "artifacts/livestock_audits.zip" not in remote
            or "artifacts/livestock_source.zip" not in remote
        ):
            raise ValueError("Missing source or audit archive")
    diagnostic = json.loads((root / "reports/livestock_mechanisms.json").read_text())
    if (
        diagnostic["study_sha256"] != digest(common)
        or diagnostic["analysis_source_sha256"]
        != file_digest(root / "scripts/diagnose_livestock_loops.py")
        or diagnostic["species_sha256"] != file_digest(root / "reports/livestock_species.csv")
        or diagnostic["products_sha256"] != file_digest(root / "reports/livestock_products.csv")
        or (diagnostic["games"], diagnostic["species_rows"], diagnostic["product_rows"])
        != (64, 192, 576)
    ):
        raise ValueError("Species/product diagnostic lineage changed")
    products = pd.read_csv(root / "reports/livestock_products.csv")
    if len(products) != 576 or products.duplicated([*KEYS, "product"]).any():
        raise ValueError("Product diagnostic keys incomplete or duplicated")
    if not (
        products.initial + products.harvested + products.collected + products.bought
        == products.sold + products.fed + products.applied + products.discarded + products.terminal
    ).all():
        raise ValueError("Public product-specific conservation failed")
    recovery = json.loads((root / "reports/livestock_recovery_probe.json").read_text())
    if (
        not recovery["restored_missing_game"]
        or not recovery["reused_existing_game"]
        or recovery["games_executed"] != 0
        or recovery["study_sha256"] != digest(common)
        or recovery["restore_code_sha256"]
        != file_digest(root / "scripts/restore_livestock_checkpoints.py")
        or recovery["sha256"] != {a["path"]: a["sha256"] for a in manifests}[recovery["path"]]
    ):
        raise ValueError("Actual S3 recovery evidence differs")
    runtime = json.loads((root / "reports/livestock_runtime.json").read_text())
    if (
        runtime["games_executed"] != 0
        or runtime["feature_vectors_matched"] != 181
        or runtime["history_state_update"]["samples"] != 719
        or runtime["analysis_code_sha256"]
        != file_digest(root / "scripts/profile_livestock_features.py")
        or runtime["episode_sha256"]
        != {a["path"]: a["sha256"] for a in manifests}[runtime["episode_path"]]
    ):
        raise ValueError("Full feature-pipeline timing evidence differs")
    slices = json.loads((root / "reports/livestock_slice_progress.json").read_text())
    if (
        slices["completed_games"] != 64
        or not slices["complete"]
        or slices["adapter_sha256"] != file_digest(root / "scripts/run_livestock_slice.py")
    ):
        raise ValueError("Operational recovery adapter or completion evidence changed")


if __name__ == "__main__":
    verify(Path(__file__).resolve().parents[1])
    print("Verified livestock study: 64 games, 1500 candidates, paired effects and replay.")
