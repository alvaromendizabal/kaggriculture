"""Bounded, resumable byte verification of exactly the registered private artifacts."""

import argparse
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from verify_supply_storage import verify_download

from kaggriculture_research.artifacts import (
    digest,
    file_digest,
    load_checkpoint,
    save_checkpoint,
    write_atomic,
    write_json,
)
from kaggriculture_terminal.experiment import job_plan, validate_episode

PREFIX = "runs/terminal-routing-20260910/"


def expected_paths(root: Path) -> list[str]:
    registration = json.loads((root / "reports/terminal_registration.json").read_text())
    paths = [j["path"] for j in registration["identity"]["jobs"]]
    paths += ["artifacts/terminal_source.zip", "reports/terminal_registration.json"]
    report = root / "reports/terminal_research.json"
    if report.exists():
        paths += [
            json.loads(report.read_text())["screening"]["matrix_artifact"]["path"],
            "artifacts/terminal_audits.zip",
        ]
        paths += [
            "reports/terminal_" + name
            for name in (
                "research.json",
                "games.csv",
                "effects.csv",
                "registry.csv",
                "correlations.csv",
                "integrity.json",
                "action_identities.csv",
                "diagnostics.json",
                "recovery.json",
            )
        ]
    return sorted(paths)


def safe_url(url: str, bucket: str, relative: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname
        not in {f"{bucket}.s3.us-west-2.amazonaws.com", f"{bucket}.s3.amazonaws.com"}
        or unquote(parsed.path) != "/" + PREFIX + relative
    ):
        raise ValueError("Download does not match the exact owned object")


def restore(root: Path, relative: str, url: str, destination: Path) -> dict:
    """Restore one verified registered game into an explicit recovery directory."""
    import hashlib
    import urllib.error
    import urllib.request

    protocol = json.loads((root / "configs/terminal_research.json").read_text())
    _, jobs = job_plan(root, protocol)
    job = next(j for j in jobs if j["path"] == relative)
    receipts = json.loads((root / "reports/terminal_uploads.json").read_text())
    expected = receipts["artifacts"][relative]
    safe_url(url, receipts["bucket"], relative)
    if destination.exists():
        if file_digest(destination) != expected["sha256"]:
            raise ValueError("Existing recovery destination differs")
        payload = load_checkpoint(destination, job["lineage"])
        if payload is None:
            raise ValueError("Recovered checkpoint lineage differs")
        validate_episode(payload, job["key"])
        return {"path": relative, "restored_games": 0, "reused_games": 1, "new_games": 0}
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read()
            version = response.headers.get("x-amz-version-id")
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Recovery stopped: HTTP {error.code}") from None
    except urllib.error.URLError:
        raise RuntimeError("Recovery transfer unavailable") from None
    if (
        hashlib.sha256(content).hexdigest() != expected["sha256"]
        or version != expected["version_id"]
    ):
        raise ValueError("Recovery content or version differs")
    temporary = destination.with_suffix(".pending")
    write_atomic(temporary, content)
    payload = load_checkpoint(temporary, job["lineage"])
    if payload is None:
        raise ValueError("Recovery lineage differs")
    validate_episode(payload, job["key"])
    temporary.replace(destination)
    return {
        "path": relative,
        "restored_games": 1,
        "reused_games": 0,
        "new_games": 0,
        "sha256": expected["sha256"],
        "semantic_sha256": payload["semantic_sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--downloads", type=Path, required=True)
    parser.add_argument("--max-new-objects", type=int, default=4)
    parser.add_argument("--recovery-probe", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.max_new_objects <= 16:
        raise ValueError("Verification slice must be in 1..16")
    root = Path(__file__).resolve().parents[1]
    urls = json.loads(args.downloads.read_text())["downloads"]
    receipt = json.loads((root / "reports/terminal_uploads.json").read_text())
    bucket = json.loads((root / "configs/aws.json").read_text())["bucket"]
    if receipt["bucket"] != bucket or receipt["prefix"] != PREFIX:
        raise ValueError("Storage identity differs")
    if args.recovery_probe:
        relative = next(iter(urls))
        target = root / "artifacts/terminal_recovery_probe" / Path(relative).name
        result = [restore(root, relative, urls[relative], target) for _ in range(2)]
        write_json(
            root / "reports/terminal_recovery.json",
            {"attempts": result, "source_sha256": file_digest(Path(__file__)), "new_games": 0},
        )
        print(json.dumps(result))
        return
    verified, new = [], 0
    for relative in expected_paths(root):
        expected = receipt["artifacts"].get(relative)
        if expected is None:
            continue
        if file_digest(root / relative) != expected["sha256"]:
            raise ValueError("Local artifact differs from upload receipt: " + relative)
        lineage = {
            "bucket": bucket,
            "key": PREFIX + relative,
            "receipt": expected,
            "verifier_sha256": file_digest(Path(__file__)),
            "download_helper_sha256": file_digest(root / "scripts/verify_supply_storage.py"),
        }
        cache = root / "artifacts/terminal_cloud_checks" / (digest(lineage) + ".json.gz")
        result = load_checkpoint(cache, lineage)
        if result is None:
            if relative not in urls or new >= args.max_new_objects:
                continue
            safe_url(urls[relative], bucket, relative)
            result = verify_download(
                {"path": relative, "key": PREFIX + relative, "url": urls[relative]}, expected
            )
            save_checkpoint(cache, lineage, result)
            new += 1
        verified.append(result)
    expected = expected_paths(root)
    result = {
        "bucket": bucket,
        "prefix": PREFIX,
        "objects_verified": len(verified),
        "expected_objects": len(expected),
        "complete": len(verified) == len(expected),
        "artifacts": verified,
        "verifier_sha256": file_digest(Path(__file__)),
        "new_downloads": new,
        "expected_paths": expected,
    }
    write_json(root / "reports/terminal_cloud_verification.json", result)
    print(json.dumps({k: v for k, v in result.items() if k not in ("artifacts", "expected_paths")}))


if __name__ == "__main__":
    main()
