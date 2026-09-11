"""Audit new decision features against saved development observations; run zero games."""

import argparse
import gzip
import hashlib
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import boto3
import numpy as np
import pandas as pd
from botocore.config import Config

from kaggriculture_research.artifacts import load_checkpoint, write_json
from kaggriculture_research.environment import game
from kaggriculture_runtime.bottlenecks import assignment_bottlenecks
from kaggriculture_staffing.experiment import validate_episode
from kaggriculture_staffing.features import canonical_observation
from kaggriculture_terminal.routing import ITEMS, WORK_VALUE, menus


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    evidence = args.evidence_root.resolve()
    started = time.monotonic()
    progress = json.loads((evidence / "reports/staffing_progress.json").read_text())
    registration = json.loads((evidence / "reports/staffing_registration.json").read_text())
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if progress["completed_games"] != 7 or progress["complete"]:
        raise ValueError("This audit is scoped to the seven preserved interrupted-pilot games")
    rows, latencies, games = [], [], []
    for artifact in progress["artifact_manifest"]:
        path = evidence / artifact["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
            raise ValueError("Preserved checkpoint bytes changed")
        key = {k: artifact[k] for k in ("seed", "seat", "opponent", "arm")}
        payload = load_checkpoint(path, {**progress["lineage"], **key})
        if payload is None:
            raise ValueError("Checkpoint lineage differs")
        validate_episode(payload, key)
        samples = {s["step"]: s["values"] for s in payload["feature_samples"]}
        for record in payload["records"]:
            if record["player"] != key["seat"] or record["observation"]["day"] != 29:
                continue
            if time.monotonic() - started > 120:
                raise TimeoutError("120-second saved-observation audit cap")
            obs = canonical_observation(record["observation"])
            tick = time.perf_counter()
            menu, meta = menus(obs)
            values = assignment_bottlenecks(
                menu,
                int(meta["room"]),
                obs["market"]["inventory"],
                ITEMS,
                game.market_price,
                WORK_VALUE,
            )
            latencies.append((time.perf_counter() - tick) * 1000)
            reference = samples[obs["step"]]
            if values["bottleneck.best_utility"] != reference["staffing.joint_utility"]:
                raise ValueError("Counterfactual base utility differs from frozen evidence")
            if values["bottleneck.feasible_plans"] != reference["staffing.assignment_leaves"]:
                raise ValueError("Counterfactual feasible set differs from frozen evidence")
            rows.append({**key, "step": obs["step"], **values})
        games.append(key)
        print(
            f"{datetime.now(UTC).isoformat()} FEATURES {len(games)}/7 states={len(rows)}",
            flush=True,
        )
    frame = pd.DataFrame(rows)
    columns = [c for c in frame if c.startswith("bottleneck.")]
    if len(rows) != 161 or len(columns) != 39:
        raise ValueError("Expected 161 saved states and the 39-column schema")
    registry = []
    for name in columns:
        per_group = frame.groupby(["seed", "seat", "arm"])[name].nunique()
        registry.append(
            {
                "feature": name,
                "distinct_values": int(frame[name].nunique()),
                "minimum": float(frame[name].min()),
                "maximum": float(frame[name].max()),
                "nonzero_fraction": float((frame[name] != 0).mean()),
                "groups_with_variation": int((per_group > 1).sum()),
                "status": "provisional_no_predictive_ablation",
            }
        )
    registry_frame = pd.DataFrame(registry)
    varying = registry_frame.loc[registry_frame.distinct_values > 1, "feature"].tolist()
    corr = frame[varying].corr(method="spearman").to_numpy()
    high_pairs = int(np.triu(np.abs(corr) >= 0.995, k=1).sum())
    selected = [f"bottleneck.worker{i}_removal_loss" for i in range(4)] + [
        "bottleneck.capacity_minus5_utility_delta",
        "bottleneck.resource_loss_max",
        "bottleneck.runner_up_utility_gap",
    ]
    group_means = frame.groupby(["seed", "seat", "arm"])[selected].mean().reset_index()
    report = {
        "status": "SAVED_OBSERVATION_FEATURE_AUDIT_PASSED",
        "source_commit": source,
        "audited_at_utc": datetime.now(UTC).isoformat(),
        "new_games": 0,
        "accepted_source_games": 7,
        "original_planned_games": 8,
        "original_pilot_status": "HALTED_LATENCY_LIMIT",
        "registration_identity_sha256": registration["identity_sha256"],
        "observations": len(rows),
        "candidate_columns": len(columns),
        "varying_columns": len(varying),
        "constant_columns": len(columns) - len(varying),
        "high_spearman_pairs": high_pairs,
        "base_assignment_parity_states": len(rows),
        "latency_including_menu_ms": {
            "median": float(np.median(latencies)),
            "p95": float(np.quantile(latencies, 0.95)),
            "max": max(latencies),
        },
        "elapsed_seconds": time.monotonic() - started,
        "group_means": group_means.to_dict("records"),
        "final_selected_features": 0,
        "official_metric_effect_measured": False,
        "validation_or_holdout_used": False,
        "feature_completion_gate": "open_research",
        "limitations": [
            "Seven accepted episodes from a latency-censored eight-game development pilot",
            "Same retained route menu only; not global optimality or a valuation of unseen routes",
            "Capacity increases are hypothetical sensitivities, not purchasable game actions",
            (
                "No fitted model or policy ablation; coverage and algebraic parity "
                "are not win-rate gains"
            ),
            "Seed 1601 was exercised in CI before original AWS registration",
        ],
    }
    (root / "reports").mkdir(exist_ok=True)
    (root / "artifacts").mkdir(exist_ok=True)
    sample = root / "artifacts/bottleneck_features.csv.gz"
    with gzip.open(sample, "wt") as handle:
        frame.to_csv(handle, index=False)
    registry_frame.to_csv(root / "reports/bottleneck_registry.csv", index=False)
    write_json(root / "reports/bottleneck_research.json", report)
    bucket = json.loads((root / "configs/aws.json").read_text())["bucket"]
    prefix = "runs/staffing-controlled-routing-20260911/"
    client = boto3.client(
        "s3",
        region_name="us-west-2",
        config=Config(connect_timeout=5, read_timeout=15, retries={"max_attempts": 2}),
    )
    receipts = {}
    outputs = [
        sample,
        root / "reports/bottleneck_registry.csv",
        root / "reports/bottleneck_research.json",
    ]
    for path in outputs:
        content = path.read_bytes()
        relative = path.relative_to(root).as_posix()
        response = client.put_object(
            Bucket=bucket, Key=prefix + relative, Body=content, ServerSideEncryption="AES256"
        )
        version = response.get("VersionId")
        if not version:
            raise ValueError("S3 version missing")
        remote = client.get_object(Bucket=bucket, Key=prefix + relative, VersionId=version)
        if hashlib.sha256(remote["Body"].read()).digest() != hashlib.sha256(content).digest():
            raise ValueError("S3 readback differs")
        receipts[relative] = {
            "version_id": version,
            "sha256": hashlib.sha256(content).hexdigest(),
            "bytes": len(content),
            "readback_verified": True,
        }
    write_json(root / "reports/bottleneck_uploads.json", receipts)
    client.put_object(
        Bucket=bucket,
        Key=prefix + "reports/bottleneck_uploads.json",
        Body=(root / "reports/bottleneck_uploads.json").read_bytes(),
        ServerSideEncryption="AES256",
    )
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
