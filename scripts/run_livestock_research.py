"""Register, execute at most eight new games, or summarize the frozen livestock study."""

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from kaggriculture_livestock.experiment import job_plan, run_batch, summarize
from kaggriculture_research.artifacts import digest, file_digest, write_json
from kaggriculture_research.progress import Progress


def register(root: Path, protocol: dict) -> dict:
    common, jobs = job_plan(root, protocol)
    path = root / "reports/livestock_registration.json"
    identity = {
        "lineage": common,
        "runner_sha256": file_digest(Path(__file__)),
        "jobs": [{"key": j["key"], "path": j["path"]} for j in jobs],
    }
    if path.exists():
        registration = json.loads(path.read_text())
        if registration["identity"] != identity or registration["identity_sha256"] != digest(
            identity
        ):
            raise ValueError("Preregistered source/protocol changed; do not reuse or overwrite")
        return registration
    if any((root / j["path"]).exists() for j in jobs):
        raise ValueError("Cannot call a study preregistered after episodes already exist")
    registration = {
        "registered_at_utc": datetime.now(UTC).isoformat(),
        "identity": identity,
        "identity_sha256": digest(identity),
        "outcomes_inspected_before_registration": False,
        "feature_completion_gate": "closed",
    }
    write_json(path, registration)
    return registration


def upload_callback(root: Path, manifest_path: Path):
    """Use task-scoped signed PUTs; never log signed URLs or persist them in the repo."""
    manifest = json.loads(manifest_path.read_text())
    uploads = manifest["uploads"]
    receipt_path = root / "reports/livestock_uploads.json"
    receipt = (
        json.loads(receipt_path.read_text())
        if receipt_path.exists()
        else {"bucket": manifest["bucket"], "prefix": manifest["prefix"], "artifacts": {}}
    )
    if (receipt["bucket"], receipt["prefix"]) != (manifest["bucket"], manifest["prefix"]):
        raise ValueError("Upload destination changed")

    def ready(path: Path) -> None:
        relative, sha = path.relative_to(root).as_posix(), file_digest(path)
        if relative in receipt["artifacts"] and receipt["artifacts"][relative]["sha256"] == sha:
            return
        if relative not in uploads:
            raise ValueError(f"Missing signed upload authorization for {relative}")
        content = path.read_bytes()
        request = urllib.request.Request(uploads[relative], data=content, method="PUT")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                etag = response.headers.get("ETag", "").strip('"')
                version = response.headers.get("x-amz-version-id")
        except urllib.error.HTTPError as error:
            # A denial is a stop condition, not a reason to find alternate credentials.
            raise RuntimeError(
                f"Checkpoint upload failed with HTTP {error.code}: {relative}"
            ) from None
        except urllib.error.URLError:
            raise RuntimeError(f"Checkpoint upload unavailable: {relative}") from None
        if etag != hashlib.md5(content, usedforsecurity=False).hexdigest() or not version:
            raise ValueError("Single-part S3 upload checksum or version receipt differs")
        receipt["artifacts"][relative] = {
            "sha256": sha,
            "bytes": len(content),
            "etag": etag,
            "version_id": version,
            "uploaded_at_utc": datetime.now(UTC).isoformat(),
        }
        write_json(receipt_path, receipt)

    return ready


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("plan", "register", "batch", "summarize", "upload"))
    parser.add_argument("--uploads", type=Path)
    parser.add_argument("--paths", nargs="*", default=[])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/livestock_research.json").read_text())
    if args.mode == "plan":
        _, jobs = job_plan(root, protocol)
        print(json.dumps([{"key": j["key"], "path": j["path"]} for j in jobs]))
        return
    if args.mode == "register":
        registration = register(root, protocol)
        print(json.dumps({k: registration[k] for k in ("registered_at_utc", "identity_sha256")}))
        return
    if not (root / "reports/livestock_registration.json").exists():
        raise ValueError("Register the study before execution")
    register(root, protocol)  # Recheck immutable code and design, without overwriting.
    ready = upload_callback(root, args.uploads) if args.uploads else None
    progress = Progress(protocol["heartbeat_seconds"])
    if args.mode == "batch":
        if ready is None:
            raise ValueError("Research execution requires an authorized durable checkpoint sink")
        result = run_batch(root, protocol, progress, ready)
        print(
            json.dumps(
                {k: result[k] for k in ("complete", "completed_games", "new_games", "reused_games")}
            )
        )
    elif args.mode == "summarize":
        with progress.stage("livestock_summary_and_joint_feature_screen"):
            result = summarize(root, protocol)
        print(
            json.dumps(
                {"games": result["games"], "feature_gate": result["feature_completion_gate"]}
            )
        )
    else:
        if ready is None or not args.paths:
            raise ValueError("Upload requires signed destinations and explicit relative paths")
        for relative in args.paths:
            path = (root / relative).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError("Upload path is outside the project")
            ready(path)
        print(json.dumps({"uploaded_or_verified": len(args.paths)}))


if __name__ == "__main__":
    main()
