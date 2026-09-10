"""Explicit public/private evidence modes and one narrow notebook source migration.

Receipts attest to an earlier download audit; they never stand in for reading
private bytes in the current kernel. No experiment or feature source is changed.
"""

from pathlib import Path, PurePosixPath

from kaggriculture_research.artifacts import digest, file_digest

ARCHIVED_FIRST17_SHA256 = "45952532e959648cb3bbc79adb8a55aa39eaab68549532790babb520ed6f14ff"
ORIGINAL_CELL = """for artifact in report["artifact_manifest"]:
    assert file_digest(root / artifact["path"]) == artifact["sha256"], artifact["path"]
print("Verified", len(report["artifact_manifest"]), "private episode artifacts against the report.")
for limitation in report["limitations"]:
    print("•", limitation)"""
PUBLIC_CELL = """import sys

sys.path.insert(0, str(root / "scripts"))
from notebook_provenance import verify_private_artifacts

receipt1 = json.loads((root / "reports/cloud_verification.json").read_text())
evidence1 = verify_private_artifacts(root, report["artifact_manifest"], receipt1)
print("Private episode files SHA-verified in this kernel:", evidence1["local_bytes_verified"])
print("Episode hashes matched to prior download audit:", evidence1["receipt_only_verified"])
if evidence1["receipt_only_verified"]:
    print("Receipt-only private bytes were NOT reread in this kernel.")
for limitation in report["limitations"]:
    print("•", limitation)"""


def verify_private_artifacts(root: Path, artifacts: list[dict], receipt: dict) -> dict:
    """Check every manifest entry; existing corrupt files must fail, never fall back."""
    run = receipt.get("run", {})
    verification = receipt.get("verification", {})
    recorded = run.get("artifacts", [])
    steps = run.get("steps", [])
    if (
        run.get("status") != "completed"
        or not steps
        or any(step.get("status") != "passed" for step in steps)
        or verification.get("all_semantic_hashes_verified") is not True
        or verification.get("downloaded_and_sha256_verified_artifacts") != len(recorded)
        or not recorded
    ):
        raise ValueError("Prior private-artifact download audit is missing or incomplete")
    indexed = {a["path"]: a for a in recorded}
    if len(indexed) != len(recorded):
        raise ValueError("Duplicate paths in prior download receipt")
    if not artifacts or len({a["path"] for a in artifacts}) != len(artifacts):
        raise ValueError("Empty or duplicated private episode manifest")
    counts = {"local_bytes_verified": 0, "receipt_only_verified": 0}
    for artifact in artifacts:
        relative = PurePosixPath(artifact["path"])
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not relative.parts
            or relative.parts[0] != "artifacts"
        ):
            raise ValueError("Unsafe private artifact path")
        recorded_artifact = indexed.get(artifact["path"], {})
        expected = artifact["sha256"]
        if (
            len(expected) != 64
            or any(c not in "0123456789abcdef" for c in expected)
            or recorded_artifact.get("sha256") != expected
            or not isinstance(recorded_artifact.get("bytes"), int)
            or recorded_artifact["bytes"] <= 0
        ):
            raise ValueError(f"Private artifact differs from prior receipt: {relative}")
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Private artifact path escapes the project or is a symlink")
        if path.exists():
            if (
                not path.is_file()
                or path.stat().st_size != recorded_artifact["bytes"]
                or file_digest(path) != expected
            ):
                raise ValueError(f"Local private artifact is corrupt: {relative}")
            counts["local_bytes_verified"] += 1
        else:
            counts["receipt_only_verified"] += 1
    return counts


def archived_study_sources(cells: list, *, require_migration: bool = False) -> list[str]:
    """Reconstruct and verify archived sources, permitting ONLY the declared cell-7 edit.

    This is source lineage verification, not a claim that the current notebook
    is byte-identical to the original AWS execution artifact.
    """
    sources = [cell.source for cell in cells]
    if len(sources) != 17:
        raise ValueError("Expected exactly 17 earlier study code cells")
    if sources[6] == PUBLIC_CELL:
        sources[6] = ORIGINAL_CELL
    elif require_migration or sources[6] != ORIGINAL_CELL:
        raise ValueError("Undeclared provenance-cell source change")
    if digest(sources) != ARCHIVED_FIRST17_SHA256:
        raise ValueError("Earlier study source changed outside the declared provenance adapter")
    return sources


def migrate_study1_provenance(cells: list) -> None:
    """Clear stale output when applying the sole declared source change."""
    archived_study_sources(cells)
    if cells[6].source != PUBLIC_CELL:
        cells[6].source = PUBLIC_CELL
        cells[6].execution_count = None
        cells[6].outputs = []
        cells[6].metadata.pop("execution", None)


def migration_record(cells: list) -> dict:
    archived = archived_study_sources(cells, require_migration=True)
    return {
        "changed_code_cell_numbers": [7],
        "reason": "Explicit local-byte versus prior-download-receipt verification",
        "unchanged_earlier_code_cells": 16,
        "archived_first17_source_sha256": digest(archived),
        "current_first17_source_sha256": digest([cell.source for cell in cells]),
        "original_cell7_source_sha256": digest(ORIGINAL_CELL),
        "current_cell7_source_sha256": digest(PUBLIC_CELL),
        "adapter_source_sha256": file_digest(Path(__file__)),
    }
