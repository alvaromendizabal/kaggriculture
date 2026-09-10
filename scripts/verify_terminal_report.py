"""Credential-free verification of terminal study source, pairing and published receipts."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from run_terminal_research import register
from verify_terminal_storage import expected_paths

from kaggriculture_research.artifacts import digest, file_digest
from kaggriculture_terminal.experiment import ARMS, KEYS, job_plan, paired_summary


def verify(root: Path, require_cloud: bool = True) -> dict:
    protocol = json.loads((root / "configs/terminal_research.json").read_text())
    registration = register(root, protocol)
    common, jobs = job_plan(root, protocol)
    report = json.loads((root / "reports/terminal_research.json").read_text())
    if report["lineage"] != common or report["games"] != 48:
        raise ValueError("Study source or count changed")
    frame = pd.read_csv(root / "reports/terminal_games.csv")
    expected_keys = {tuple(j["key"][k] for k in KEYS) for j in jobs}
    if (
        len(frame) != 48
        or set(frame[list(KEYS)].itertuples(index=False, name=None)) != expected_keys
    ):
        raise ValueError("Registered job identities differ")
    if not np.isfinite(frame.select_dtypes("number")).all().all():
        raise ValueError("Missing or nonfinite results")
    for _, block in frame.groupby(["seed", "seat", "opponent"]):
        if set(block.arm) != set(ARMS):
            raise ValueError("Incomplete paired block")
    if not (
        frame.match_score == (frame.coin_margin > 0).astype(float) + 0.5 * (frame.coin_margin == 0)
    ).all():
        raise ValueError("Match score differs from official terminal money")
    effects = paired_summary(frame, protocol["bootstrap_resamples"], protocol["bootstrap_seed"])
    saved = pd.read_csv(root / "reports/terminal_effects.csv")
    pd.testing.assert_frame_equal(effects, saved, check_dtype=False, rtol=1e-10, atol=1e-10)
    pd.testing.assert_frame_equal(effects, pd.DataFrame(report["effects"]), check_dtype=False)
    groups = (
        frame.groupby(["opponent", "arm"])
        .mean(numeric_only=True)
        .drop(columns=["seed", "seat"])
        .reset_index()
    )
    pd.testing.assert_frame_equal(groups, pd.DataFrame(report["groups"]), check_dtype=False)
    prefixes = (
        pd.DataFrame(report["artifact_manifest"])
        .groupby(["seed", "seat", "opponent"])["preterminal_sha256"]
        .nunique()
    )
    if (
        len(prefixes) != 16
        or not (prefixes == 1).all()
        or report["identical_preterminal_blocks"] != 16
    ):
        raise ValueError("Preterminal intervention isolation failed")
    registry = pd.read_csv(root / "reports/terminal_registry.csv")
    if (
        len(registry) != 1579
        or registry.feature.duplicated().any()
        or registry.feature.str.startswith("cash_history.").any()
    ):
        raise ValueError("Supported feature schema differs")
    if registry.feature.str.startswith("terminal.").sum() != 79:
        raise ValueError("New feature family count differs")
    screening = report["screening"]
    if (
        screening["sampled_development_observations"] != 8688
        or screening["retained_for_final_model"]
    ):
        raise ValueError("Screening scope differs")
    if set(screening["constant_features"]) != set(
        registry.loc[registry.distinct_development_values <= 1, "feature"]
    ):
        raise ValueError("Constant screening differs")
    audit = json.loads((root / "reports/terminal_integrity.json").read_text())
    if (
        not audit["complete"]
        or audit["games_audited"] != 48
        or audit["mismatches"]
        or audit["study_sha256"] != digest(common)
        or audit["audit_code_sha256"] != file_digest(root / "scripts/audit_terminal_evidence.py")
    ):
        raise ValueError("Independent audit identity differs")
    expected_counts = {
        "callbacks": 48 * 719,
        "feature_vectors": 48 * 181,
        "state_restores": 48 * 31,
        "private_transitions": 48 * 1438,
        "product_balances": 48 * 18,
        "stock_checks": 48 * 5033,
        "sale_checks": 48 * 5026,
    }
    if audit["counts"] != expected_counts:
        raise ValueError("Independent audit coverage incomplete")
    recovery = json.loads((root / "reports/terminal_recovery.json").read_text())
    if (
        recovery["new_games"]
        or recovery["attempts"][0]["restored_games"] != 1
        or recovery["attempts"][1]["reused_games"] != 1
        or recovery["source_sha256"] != file_digest(root / "scripts/verify_terminal_storage.py")
    ):
        raise ValueError("Actual cloud recovery proof differs")
    receipts = json.loads((root / "reports/terminal_uploads.json").read_text())
    registered = receipts["artifacts"]["reports/terminal_registration.json"]["uploaded_at_utc"]
    source = receipts["artifacts"]["artifacts/terminal_source.zip"]["uploaded_at_utc"]
    for artifact in report["artifact_manifest"]:
        receipt = receipts["artifacts"][artifact["path"]]
        if receipt["sha256"] != artifact["sha256"] or receipt["uploaded_at_utc"] <= max(
            registered, source
        ):
            raise ValueError("Outcomes precede durable registration/source")
    if require_cloud:
        cloud = json.loads((root / "reports/terminal_cloud_verification.json").read_text())
        if not cloud["complete"] or cloud["verifier_sha256"] != file_digest(
            root / "scripts/verify_terminal_storage.py"
        ):
            raise ValueError("Cloud verification incomplete or stale")
        if set(expected_paths(root)) != {a["path"] for a in cloud["artifacts"]}:
            raise ValueError("Cloud object set differs")
        for item in cloud["artifacts"]:
            receipt = receipts["artifacts"][item["path"]]
            if (
                any(item[k] != receipt[k] for k in ("sha256", "bytes", "version_id", "etag"))
                or item["encryption"] != "AES256"
            ):
                raise ValueError("Cloud bytes/version/encryption differs")
            if (
                item["path"].startswith("reports/")
                and file_digest(root / item["path"]) != item["sha256"]
            ):
                raise ValueError("Published evidence differs from cloud verification")
    return {
        "registered_games": 48,
        "features": 1579,
        "new_features": 79,
        "audited_games": 48,
        "identical_preterminal_blocks": 16,
        "registration_sha256": registration["identity_sha256"],
        "feature_gate": "open_research",
    }


if __name__ == "__main__":
    print(json.dumps(verify(Path(__file__).resolve().parents[1])))
