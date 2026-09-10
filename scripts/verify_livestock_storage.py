"""Verify all registered episodes, analysis and audit archive against S3 bytes."""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from verify_supply_storage import verify_download

from kaggriculture_research.artifacts import (
    digest,
    file_digest,
    load_checkpoint,
    save_checkpoint,
    write_json,
)
from kaggriculture_research.progress import Progress


def required_paths(root: Path) -> set[str]:
    report = json.loads((root / "reports/livestock_research.json").read_text())
    paths = {a["path"] for a in report["artifact_manifest"]}
    paths.add(report["screening"]["matrix_artifact"]["path"])
    paths.update({"artifacts/livestock_source.zip", "artifacts/livestock_audits.zip"})
    paths.update(
        "reports/livestock_" + name
        for name in (
            "games.csv",
            "effects.csv",
            "registry.csv",
            "correlations.csv",
            "research.json",
            "integrity.json",
            "action_identities.csv",
            "registration.json",
            "preflight.json",
            "recovery_probe.json",
            "runtime.json",
            "slice_progress.json",
            "mechanisms.json",
            "species.csv",
            "products.csv",
        )
    )
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--downloads", type=Path, required=True)
    parser.add_argument("--max-new-objects", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.max_new_objects <= 82:
        raise ValueError("Verification batch must contain 1–82 objects")
    root = Path(__file__).resolve().parents[1]
    uploads = json.loads((root / "reports/livestock_uploads.json").read_text())
    items = json.loads(args.downloads.read_text())["downloads"]
    if len(items) != len(required_paths(root)) or {i["path"] for i in items} != required_paths(
        root
    ):
        raise ValueError("Remote evidence set incomplete or duplicated")
    for item in items:
        key = (
            "releases/livestock-resource-loops/source.zip"
            if item["path"] == "artifacts/livestock_source.zip"
            else uploads["prefix"] + item["path"]
        )
        if (
            item["key"] != key
            or file_digest(root / item["path"]) != uploads["artifacts"][item["path"]]["sha256"]
        ):
            raise ValueError("Unexpected destination or changed local artifact")
    results, pending = [], []
    for item in items:
        lineage = {
            "bucket": uploads["bucket"],
            "key": item["key"],
            "path": item["path"],
            "upload_receipt": uploads["artifacts"][item["path"]],
            "verification_code_sha256": file_digest(Path(__file__)),
            "download_verifier_sha256": file_digest(root / "scripts/verify_supply_storage.py"),
        }
        cache = root / "artifacts/livestock_storage_checks" / (digest(lineage) + ".json.gz")
        cached = load_checkpoint(cache, lineage)
        if cached is None:
            pending.append((item, lineage, cache))
        else:
            results.append(cached)
    # Save each verified object immediately: an interrupted transfer must not
    # invalidate or repeat unrelated completed downloads.
    with Progress().stage("verify_livestock_s3_bytes_versions_and_encryption"):
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(verify_download, item, uploads["artifacts"][item["path"]]): (
                    lineage,
                    cache,
                )
                for item, lineage, cache in pending[: args.max_new_objects]
            }
            for future in as_completed(futures):
                checked = future.result()
                checked["download_verified_at_utc"] = datetime.now(UTC).isoformat()
                lineage, cache = futures[future]
                save_checkpoint(cache, lineage, checked)
                results.append(checked)
    if len(results) != len(items):
        print(
            json.dumps(
                {"verified_objects": len(results), "required": len(items), "complete": False}
            )
        )
        return
    results.sort(key=lambda r: r["path"])
    result = {
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "bucket": uploads["bucket"],
        "prefix": uploads["prefix"],
        "registration_sha256": file_digest(root / "reports/livestock_registration.json"),
        "compute_used": "local_cpu_no_additional_aws_compute",
        "verification_scope": (
            "per-object byte checks bound to exact upload version and verifier source"
        ),
        "artifacts": results,
        "verification_code_sha256": file_digest(Path(__file__)),
        "download_verifier_sha256": file_digest(root / "scripts/verify_supply_storage.py"),
        "total_bytes_verified": sum(r["bytes"] for r in results),
    }
    write_json(root / "reports/livestock_cloud_verification.json", result)
    print(
        json.dumps(
            {"artifacts_verified": len(results), "bytes_verified": result["total_bytes_verified"]}
        )
    )


if __name__ == "__main__":
    main()
