"""Verify every saved S3 byte by SHA-256, version and encryption before publication."""

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from kaggriculture_research.artifacts import file_digest, write_json
from kaggriculture_research.progress import Progress


def verify_download(item: dict, receipt: dict) -> dict:
    try:
        with urllib.request.urlopen(item["url"], timeout=60) as response:
            content = response.read()
            headers = response.headers
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"S3 verification stopped: HTTP {error.code}") from None
    except urllib.error.URLError:
        raise RuntimeError("S3 verification unavailable") from None
    sha = hashlib.sha256(content).hexdigest()
    version = headers.get("x-amz-version-id")
    encryption = headers.get("x-amz-server-side-encryption")
    etag = headers.get("ETag", "").strip('"')
    if (
        sha != receipt["sha256"]
        or len(content) != receipt["bytes"]
        or version != receipt["version_id"]
        or etag != receipt["etag"]
        or encryption != "AES256"
    ):
        raise ValueError("Downloaded S3 bytes, version, or encryption differ from upload receipt")
    return {
        "path": item["path"],
        "key": item["key"],
        "sha256": sha,
        "bytes": len(content),
        "version_id": version,
        "encryption": encryption,
        "etag": etag,
        "remote_receipt_matched": True,
        "remote_bytes_sha256_verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--downloads", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    uploads = json.loads((root / "reports/supply_uploads.json").read_text())
    items = json.loads(args.downloads.read_text())["downloads"]
    report = json.loads((root / "reports/supply_research.json").read_text())
    required = {a["path"] for a in report["artifact_manifest"]}
    required.add(report["screening"]["matrix_artifact"]["path"])
    required.update(
        "reports/" + n
        for n in (
            "supply_games.csv",
            "supply_effects.csv",
            "supply_registry.csv",
            "supply_correlations.csv",
            "supply_research.json",
            "supply_integrity.json",
            "supply_bound_diagnostics.csv",
            "supply_action_identities.csv",
            "supply_registration.json",
        )
    )
    required.add("artifacts/supply_source.zip")
    if len(items) != len(required) or {i["path"] for i in items} != required:
        raise ValueError("Storage-verification manifest incomplete or duplicated")
    for item in items:
        expected_key = (
            "releases/cash-constrained-supply/source.zip"
            if item["path"] == "artifacts/supply_source.zip"
            else uploads["prefix"] + item["path"]
        )
        if item["key"] != expected_key:
            raise ValueError("Unexpected S3 destination in verification manifest")
        if file_digest(root / item["path"]) != uploads["artifacts"][item["path"]]["sha256"]:
            raise ValueError("Local artifact differs from uploaded bytes")
    progress = Progress()
    with progress.stage("verify_s3_versions_encryption_and_sha256"):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(
                pool.map(lambda i: verify_download(i, uploads["artifacts"][i["path"]]), items)
            )
    result = {
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "bucket": uploads["bucket"],
        "prefix": uploads["prefix"],
        "registration_sha256": file_digest(root / "reports/supply_registration.json"),
        "compute_used": "local_cpu_no_additional_aws_compute",
        "artifacts": results,
        "verification_code_sha256": file_digest(Path(__file__)),
        "total_bytes_verified": sum(r["bytes"] for r in results),
    }
    write_json(root / "reports/supply_cloud_verification.json", result)
    print(
        json.dumps(
            {"artifacts_verified": len(results), "bytes_verified": result["total_bytes_verified"]}
        )
    )


if __name__ == "__main__":
    main()
