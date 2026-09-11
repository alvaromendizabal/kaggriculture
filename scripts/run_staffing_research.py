"""Register, preflight, execute, summarize and durably checkpoint the staffing pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import boto3

from kaggriculture_research.artifacts import digest, file_digest, write_json
from kaggriculture_staffing.experiment import (
    job_plan,
    run_activation_preflight,
    run_batch,
    summarize,
)

PREFIX = "runs/staffing-controlled-routing-20260911/"
REGION = "us-west-2"


def repository_head(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def register(root: Path, protocol: dict) -> dict:
    """Freeze source/design before any pilot outcome exists."""
    common, jobs = job_plan(root, protocol)
    path = root / "reports/staffing_registration.json"
    identity = {
        "lineage": common,
        "runner_sha256": file_digest(Path(__file__)),
        "repository_head": repository_head(root),
        "jobs": [{"key": job["key"], "path": job["path"]} for job in jobs],
    }
    if path.exists():
        registration = json.loads(path.read_text())
        if registration["identity"] != identity or registration["identity_sha256"] != digest(
            identity
        ):
            raise ValueError("Preregistered staffing source/protocol changed")
        return registration
    if any((root / job["path"]).exists() for job in jobs):
        raise ValueError("Cannot preregister after staffing pilot episodes exist")
    registration = {
        "registered_at_utc": datetime.now(UTC).isoformat(),
        "identity": identity,
        "identity_sha256": digest(identity),
        "outcomes_inspected_before_registration": False,
        "validation_or_holdout_used": False,
        "feature_completion_gate": "open_research",
    }
    write_json(path, registration)
    return registration


class S3Store:
    """Private versioned checkpoint sink with immediate remote-byte readback."""

    def __init__(self, root: Path) -> None:
        config = json.loads((root / "configs/aws.json").read_text())
        self.root = root
        self.bucket = config["bucket"]
        self.client = boto3.client("s3", region_name=REGION)
        self.receipt_path = root / "reports/staffing_uploads.json"
        self.receipt = (
            json.loads(self.receipt_path.read_text())
            if self.receipt_path.exists()
            else {"bucket": self.bucket, "prefix": PREFIX, "artifacts": {}}
        )
        if (self.receipt["bucket"], self.receipt["prefix"]) != (self.bucket, PREFIX):
            raise ValueError("Staffing checkpoint destination changed")

    def _put_readback(self, relative: str, content: bytes) -> dict:
        key = PREFIX + relative
        response = self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ServerSideEncryption="AES256",
        )
        version_id = response.get("VersionId")
        if not version_id:
            raise ValueError("Versioned S3 receipt missing")
        remote = self.client.get_object(Bucket=self.bucket, Key=key, VersionId=version_id)
        remote_bytes = remote["Body"].read()
        if hashlib.sha256(remote_bytes).digest() != hashlib.sha256(content).digest():
            raise ValueError("S3 readback bytes differ from local checkpoint")
        if remote.get("ServerSideEncryption") != "AES256":
            raise ValueError("S3 readback encryption differs")
        return {
            "sha256": hashlib.sha256(content).hexdigest(),
            "bytes": len(content),
            "etag": response.get("ETag", "").strip('"'),
            "version_id": version_id,
            "uploaded_at_utc": datetime.now(UTC).isoformat(),
            "readback_verified": True,
        }

    def persist_receipt(self) -> None:
        write_json(self.receipt_path, self.receipt)
        self._put_readback("reports/staffing_uploads.json", self.receipt_path.read_bytes())

    def upload(self, path: Path) -> None:
        relative = path.relative_to(self.root).as_posix()
        content = path.read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        prior = self.receipt["artifacts"].get(relative)
        if prior and prior.get("sha256") == sha and prior.get("readback_verified"):
            return
        self.receipt["artifacts"][relative] = self._put_readback(relative, content)
        self.persist_receipt()


def run_preflight(root: Path, protocol: dict, registration: dict) -> dict:
    """Prove the shared base reaches a real multiworker final-day state without scoring it."""
    path = root / "reports/staffing_preflight.json"
    identity = {
        "registration_identity_sha256": registration["identity_sha256"],
        "preflight_seed": protocol["preflight_seed"],
    }
    if path.exists():
        report = json.loads(path.read_text())
        if report["identity"] != identity:
            raise ValueError("Staffing preflight identity changed")
        return report
    result = run_activation_preflight(protocol["preflight_seed"])
    if result["multiworker_callbacks"] < protocol["minimum_multiworker_callbacks"]:
        raise ValueError("Staffing preflight did not activate multiple workers")
    if result["policy_latency_ms"]["max"] > protocol["maximum_policy_latency_ms"]:
        raise ValueError("Staffing preflight exceeded policy latency budget")
    report = {
        "identity": identity,
        "status": "PASSED",
        "result": result,
        "finished_utc": datetime.now(UTC).isoformat(),
    }
    write_json(path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("plan", "register", "preflight", "batch", "summarize"))
    parser.add_argument("--durable", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/staffing_research.json").read_text())
    common, jobs = job_plan(root, protocol)
    if args.mode == "plan":
        print(json.dumps({"lineage_sha256": digest(common), "jobs": jobs}, default=str))
        return

    registration = register(root, protocol)
    store = S3Store(root) if args.durable else None
    if store:
        store.upload(root / "reports/staffing_registration.json")

    if args.mode == "register":
        print(
            json.dumps(
                {"identity_sha256": registration["identity_sha256"], "jobs": len(jobs)}
            )
        )
        return

    preflight = run_preflight(root, protocol, registration)
    if store:
        store.upload(root / "reports/staffing_preflight.json")
    if args.mode == "preflight":
        print(json.dumps(preflight))
        return

    if not args.durable:
        raise ValueError("Pilot execution and summary require --durable private S3 checkpointing")

    if args.mode == "batch":
        result = run_batch(root, protocol)
        for artifact in result["artifact_manifest"]:
            store.upload(root / artifact["path"])
        store.upload(root / "reports/staffing_progress.json")
        print(
            json.dumps(
                {
                    key: result[key]
                    for key in ("complete", "completed_games", "new_games", "reused_games")
                }
            )
        )
        return

    progress_path = root / "reports/staffing_progress.json"
    if not progress_path.exists() or not json.loads(progress_path.read_text()).get("complete"):
        raise ValueError("Cannot summarize before all registered staffing games are durable")
    report = summarize(root, protocol)
    outputs = [
        root / "reports/staffing_games.csv",
        root / "reports/staffing_effects.csv",
        root / "reports/staffing_registry.csv",
        root / "reports/staffing_correlations.csv",
        root / "reports/staffing_research.json",
        progress_path,
    ]
    for path in outputs:
        store.upload(path)
    print(json.dumps({"games": report["games"], "feature_gate": report["feature_completion_gate"]}))


if __name__ == "__main__":
    main()
