"""Audit the halted pilot from verified checkpoints, without running another game.

Run from a reviewed worktree with --evidence-root pointing at the frozen AWS
checkout. Outputs are observation/operational evidence, never an eight-game score.
"""

from __future__ import annotations

import argparse
import copy
import cProfile
import hashlib
import json
import pstats
import signal
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import boto3
import pandas as pd
from botocore.config import Config

from kaggriculture_research.artifacts import load_checkpoint, write_json
from kaggriculture_runtime.routing import assign as candidate_assign
from kaggriculture_staffing import features
from kaggriculture_staffing.experiment import job_plan, validate_episode
from kaggriculture_terminal import routing

PREFIX = "runs/staffing-controlled-routing-20260911/"
FROZEN = "f5c63727b2996f6154b07e4e26c6bfbb899d8559"


def utc() -> str:
    return datetime.now(UTC).isoformat()


def combined(obs: dict, optimized: bool) -> tuple[dict, dict, dict]:
    """Profile the same feature/route computations; never waive deployment timing."""
    if optimized:
        with patch.object(features, "assign", candidate_assign):
            vector = features.staffing_features(copy.deepcopy(obs))
        with patch.object(routing, "assign", candidate_assign):
            action, diagnostics = routing.liquidation(copy.deepcopy(obs))
    else:
        vector = features.staffing_features(copy.deepcopy(obs))
        action, diagnostics = routing.liquidation(copy.deepcopy(obs))
    return vector.values, action, diagnostics


def profile(obs: dict, optimized: bool) -> dict:
    profiler = cProfile.Profile()
    profiler.runcall(combined, obs, optimized)
    stats = pstats.Stats(profiler).stats
    ranked = sorted(stats.items(), key=lambda item: item[1][3], reverse=True)
    return {
        "total_calls": sum(value[1] for value in stats.values()),
        "market_price_calls": sum(v[1] for k, v in stats.items() if k[2] == "market_price"),
        "top_functions": [
            {"file": Path(key[0]).name, "line": key[1], "function": key[2],
             "calls": value[1], "cumulative_seconds": value[3]}
            for key, value in ranked[:8]
        ],
    }


def upload(s3, bucket: str, root: Path, path: Path) -> dict:
    content = path.read_bytes()
    key = PREFIX + path.relative_to(root).as_posix()
    put = s3.put_object(Bucket=bucket, Key=key, Body=content, ServerSideEncryption="AES256")
    version = put.get("VersionId")
    if not version:
        raise ValueError("Missing versioned audit receipt")
    get = s3.get_object(Bucket=bucket, Key=key, VersionId=version)
    remote = get["Body"].read()
    if remote != content or get.get("ServerSideEncryption") != "AES256":
        raise ValueError("Audit readback/encryption mismatch")
    return {"sha256": hashlib.sha256(content).hexdigest(), "version_id": version,
            "bytes": len(content), "readback_verified": True}


def audit(root: Path, evidence: Path) -> dict:
    started = time.monotonic()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=evidence, text=True).strip()
    if head != FROZEN:
        raise ValueError("Frozen evidence checkout moved; inspect before continuing")
    bucket = json.loads((evidence / "configs/aws.json").read_text())["bucket"]
    s3 = boto3.client("s3", region_name="us-west-2", config=Config(
        connect_timeout=5, read_timeout=15, retries={"max_attempts": 2}
    ))
    failure_object = s3.get_object(Bucket=bucket, Key=PREFIX + "wrapper.log")
    failure_log = failure_object["Body"].read().decode()
    expected_error = "Registered policy latency budget exceeded"
    if "BATCH_8" not in failure_log or expected_error not in failure_log:
        raise ValueError("Expected halted eighth-game failure was not found")
    registration = json.loads((evidence / "reports/staffing_registration.json").read_text())
    receipts = json.loads((evidence / "reports/staffing_uploads.json").read_text())
    protocol = json.loads((evidence / "configs/staffing_research.json").read_text())
    _, jobs = job_plan(evidence, protocol)
    payloads, artifacts, missing = [], [], []
    for job in jobs:
        path = evidence / job["path"]
        if not path.exists():
            missing.append(job["key"])
            continue
        receipt = receipts["artifacts"][job["path"]]
        remote = s3.get_object(Bucket=bucket, Key=PREFIX + job["path"],
                               VersionId=receipt["version_id"])
        content = remote["Body"].read()
        if hashlib.sha256(content).hexdigest() != receipt["sha256"]:
            raise ValueError("Private checkpoint bytes changed")
        if content != path.read_bytes() or remote.get("ServerSideEncryption") != "AES256":
            raise ValueError("Local/remote checkpoint or encryption mismatch")
        payload = load_checkpoint(path, job["lineage"])
        if payload is None:
            raise ValueError("Frozen checkpoint lineage mismatch")
        validate_episode(payload, job["key"])
        payloads.append(payload)
        artifacts.append({**job["key"], "path": job["path"], **receipt})
    if len(payloads) != 7 or missing != [jobs[-1]["key"]]:
        raise ValueError("Evidence is not the inspected seven-of-eight halted pilot")
    print(f"{utc()} VERIFIED_CHECKPOINTS 7/7; new_games=0", flush=True)

    rows, samples, snapshots = [], [], []
    feature_matches = route_matches = 0
    for index, payload in enumerate(payloads):
        summary = payload["summary"]
        rows.append(summary)
        records = [row for row in payload["records"] if row["player"] == summary["seat"]]
        terminal = [row for row in records if row["observation"]["day"] == 29]
        for row, sample in zip(terminal, payload["feature_samples"], strict=True):
            obs = row["observation"]
            with patch.object(features, "assign", candidate_assign):
                candidate = features.staffing_features(copy.deepcopy(obs))
            if candidate.values != sample["values"] or candidate.families != sample["families"]:
                raise ValueError("Runtime candidate changed a saved feature vector")
            feature_matches += 1
            samples.append({"seed": summary["seed"], "seat": summary["seat"],
                            "arm": summary["arm"], **sample["values"]})
            if summary["arm"] == "coordinated":
                with patch.object(routing, "assign", candidate_assign):
                    action, diagnostics = routing.liquidation(copy.deepcopy(obs))
                if any(action[name] != row["action"][name] for name in ("farmer", "hands")):
                    raise ValueError("Runtime candidate changed a saved farm action")
                if diagnostics != row["diagnostics"]["route_diagnostics"]:
                    raise ValueError("Runtime candidate changed route diagnostics")
                route_matches += 1
        if summary["arm"] == "coordinated":
            slowest = max(
                terminal, key=lambda row: payload["latency_ms"][row["observation"]["step"]]
            )
            snapshots.append({
                "identity": {name: summary[name] for name in ("seed", "seat", "arm")},
                "observation": slowest["observation"]
            })
        print(f"{utc()} PARITY {index + 1}/7 vectors={feature_matches} actions={route_matches}",
              flush=True)

    measurements = []
    for snapshot in snapshots:
        obs = snapshot["observation"]
        if combined(obs, False) != combined(obs, True):
            raise ValueError("Combined runtime-equivalence check failed")
        timing = {"reference_ms": [], "candidate_ms": []}
        for _ in range(3):
            for optimized, name in ((False, "reference_ms"), (True, "candidate_ms")):
                tick = time.perf_counter()
                combined(obs, optimized)
                timing[name].append((time.perf_counter() - tick) * 1000)
        measurements.append({**snapshot["identity"], "step": obs["step"], **timing,
                             "reference_profile": profile(obs, False),
                             "candidate_profile": profile(obs, True)})
    frame = pd.DataFrame(rows)
    frame.to_csv(root / "reports/staffing_observed_games.csv", index=False)
    matrix = pd.DataFrame(samples)
    family_map = payloads[0]["feature_samples"][0]["families"]
    registry = []
    for name, family in family_map.items():
        registry.append({"feature": name, "family": family,
                         "distinct_values": int(matrix[name].nunique()),
                         "minimum": float(matrix[name].min()), "maximum": float(matrix[name].max()),
                         "nonzero_fraction": float((matrix[name] != 0).mean()),
                         "status": "provisional_not_predictively_selected"})
    pd.DataFrame(registry).to_csv(root / "reports/staffing_feature_coverage.csv", index=False)
    pairs = []
    for (seed, seat), group in frame.groupby(["seed", "seat"]):
        if set(group.arm) != {"sequential", "coordinated"}:
            continue
        selected = [
            p for p in payloads
            if (p["summary"]["seed"], p["summary"]["seat"]) == (seed, seat)
        ]
        if len({p["preterminal_sha256"] for p in selected}) != 1:
            raise ValueError("A completed pair diverged before intervention")
        indexed = group.set_index("arm")
        pairs.append({"seed": int(seed), "seat": int(seat), "identical_preterminal": True,
                      "coin_margin_difference": float(indexed.loc["coordinated", "coin_margin"]
                                                      - indexed.loc["sequential", "coin_margin"]),
                      "match_score_difference": float(indexed.loc["coordinated", "match_score"]
                                                      - indexed.loc["sequential", "match_score"])})
    report = {
        "status": "HALTED_LATENCY_LIMIT", "audited_at_utc": utc(), "source_commit": FROZEN,
        "registration_identity_sha256": registration["identity_sha256"],
        "expected_games": 8, "accepted_games": 7, "new_games_run": 0,
        "failed_attempt": {**missing[0], "reason": "Registered policy latency budget exceeded",
                           "maximum_latency_ms": None, "outcome": None,
                           "note": "Original maximum and rejected payload were not saved"},
        "failure_log": {"version_id": failure_object["VersionId"],
                        "sha256": hashlib.sha256(failure_log.encode()).hexdigest()},
        "published_eight_game_score": None, "validation_or_holdout_used": False,
        "artifacts": artifacts, "completed_pairs": pairs,
        "feature_evidence": {"candidates": len(registry), "observations": len(matrix),
                             "varying": sum(row["distinct_values"] > 1 for row in registry),
                             "constant": sum(row["distinct_values"] == 1 for row in registry),
                             "selected_for_final_model": 0},
        "runtime_candidate": {"promoted": False, "feature_vectors_identical": feature_matches,
                              "farm_actions_and_diagnostics_identical": route_matches,
                              "measurements": measurements,
                              "scope": "Feature extraction plus routing, not end-to-end policy latency"},
        "registration_caveat": (
            "CI exercised seed 1601 before AWS registration; it is not untouched evidence"
        ),
        "feature_completion_gate": "open_research",
        "limitations": ["Latency-censored partial pilot; not an eight-game result",
                        "One opponent and two seeds cannot establish population strength",
                        "Snapshot parity is not a complete live deployment acceptance test",
                        "Original maximum-latency value and eighth-game payload were not saved"],
        "elapsed_seconds": time.monotonic() - started,
    }
    report_path = root / "reports/staffing_runtime_audit.json"
    write_json(report_path, report)
    outputs = [report_path, root / "reports/staffing_observed_games.csv",
               root / "reports/staffing_feature_coverage.csv"]
    uploaded = {p.relative_to(root).as_posix(): upload(s3, bucket, root, p) for p in outputs}
    receipt_path = root / "reports/staffing_audit_uploads.json"
    write_json(receipt_path, {"bucket": bucket, "prefix": PREFIX, "artifacts": uploaded})
    upload(s3, bucket, root, receipt_path)
    print(f"{utc()} AUDIT_COMPLETE new_games=0 accepted=7 expected=8", flush=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    (root / "reports").mkdir(exist_ok=True)

    def on_timeout(*_):
        raise TimeoutError("180s audit limit")

    signal.signal(signal.SIGALRM, on_timeout)
    signal.alarm(180)
    try:
        audit(root, args.evidence_root.resolve())
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
