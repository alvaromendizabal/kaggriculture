"""Verify the frozen publication without importing or executing research code.

This is an integrity/structure gate, not a claim of runtime correctness or a
replacement for the standalone experiment suites recorded in the snapshots.
"""

import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

LOCK = "research/PUBLICATION_CI_LOCK.json"
MANIFEST = "research/PUBLICATION_MANIFEST.json"
OVERVIEW = "notebooks/00_research_overview.ipynb"
ARCHIVE = "research/manual"


def permitted(name: str) -> bool:
    """Only the explicitly frozen publication paths can be in the lock."""
    return name.startswith(ARCHIVE + "/") or name in {MANIFEST, OVERVIEW}


def safe_path(root: Path, name: str) -> Path:
    """Reject escape paths and symlinked files or parent directories."""
    relative = PurePosixPath(name)
    if (
        not name
        or "\\" in name
        or relative.is_absolute()
        or ".." in relative.parts
        or str(relative) != name
    ):
        raise ValueError(f"Unsafe publication path: {name!r}")
    candidate = root
    for part in relative.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError(f"Symlinked publication path: {name}")
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Publication path escapes checkout: {name}")
    return candidate


def tracked_snapshot_paths(root: Path) -> set[str]:
    command = ["git", "-C", str(root), "ls-files", "-z", "--", ARCHIVE, MANIFEST, OVERVIEW]
    result = subprocess.run(command, check=True, capture_output=True, timeout=20)
    return {name for name in result.stdout.decode().split("\0") if name}


def inspect_notebook(data: bytes, name: str) -> dict[str, int]:
    """Parse notebook structure without inventing or modifying execution evidence."""
    notebook = json.loads(data)
    if notebook.get("nbformat") != 4 or not isinstance(notebook.get("cells"), list):
        raise ValueError(f"Invalid notebook structure: {name}")
    result = {"code_cells": 0, "unexecuted_cells": 0, "error_outputs": 0}
    for cell in notebook["cells"]:
        if cell.get("cell_type") not in {"code", "markdown", "raw"}:
            raise ValueError(f"Invalid notebook cell type: {name}")
        source = cell.get("source", "")
        if not isinstance(source, (str, list)):
            raise ValueError(f"Invalid notebook source field: {name}")
        if isinstance(source, list) and not all(isinstance(line, str) for line in source):
            raise ValueError(f"Invalid notebook source list: {name}")
        if cell["cell_type"] != "code":
            continue
        result["code_cells"] += 1
        count = cell.get("execution_count")
        if count is None:
            result["unexecuted_cells"] += 1
        elif type(count) is not int or count < 0:
            raise ValueError(f"Invalid execution count: {name}")
        outputs = cell.get("outputs", [])
        if not isinstance(outputs, list):
            raise ValueError(f"Invalid outputs field: {name}")
        for output in outputs:
            if not isinstance(output, dict):
                raise ValueError(f"Invalid output: {name}")
            result["error_outputs"] += int(output.get("output_type") == "error")
    return result


def verify(root: Path, tracked: set[str] | None = None) -> dict:
    """Require complete tracked coverage, exact bytes, and source/JSON structure."""
    root = root.resolve()
    lock = json.loads(safe_path(root, LOCK).read_bytes())
    if lock.get("schema_version") != 1 or not re.fullmatch(
        r"[0-9a-f]{40}", lock.get("source_commit", "")
    ):
        raise ValueError("Unsupported publication lock")
    rows = lock.get("files")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Empty or invalid publication lock")
    indexed = {}
    for row in rows:
        name = row["path"]
        if not permitted(name) or name in indexed:
            raise ValueError(f"Unexpected or duplicated locked path: {name}")
        if type(row["bytes"]) is not int or row["bytes"] < 0:
            raise ValueError(f"Invalid file size: {name}")
        if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise ValueError(f"Invalid digest: {name}")
        indexed[name] = row
    tracked = tracked_snapshot_paths(root) if tracked is None else tracked
    if tracked != set(indexed):
        missing = sorted(tracked - set(indexed))
        extra = sorted(set(indexed) - tracked)
        raise ValueError(f"Lock coverage differs; unlisted={missing}; absent={extra}")
    totals = {"python_sources": 0, "notebooks": 0, "unexecuted_cells": 0, "error_outputs": 0}
    for name, row in indexed.items():
        data = safe_path(root, name).read_bytes()
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError(f"Published bytes differ: {name}")
        if name.endswith(".py"):
            ast.parse(data.decode("utf-8-sig"), filename=name)
            totals["python_sources"] += 1
        elif name.endswith(".ipynb"):
            summary = inspect_notebook(data, name)
            totals["notebooks"] += 1
            totals["unexecuted_cells"] += summary["unexecuted_cells"]
            totals["error_outputs"] += summary["error_outputs"]
    manifest = json.loads(safe_path(root, MANIFEST).read_bytes())
    seen = set()
    for row in manifest["files"]:
        name = f"{ARCHIVE}/{row['package']}/{row['relative']}"
        safe_path(root, name)
        if name in seen or name not in indexed:
            raise ValueError(f"Manifest coverage differs: {name}")
        seen.add(name)
        expected = indexed[name]
        if row["bytes"] != expected["bytes"] or row["sha256"] != expected["sha256"]:
            raise ValueError(f"Original publication manifest disagrees: {name}")
    return {
        "status": "PUBLICATION_SNAPSHOT_VERIFIED",
        "locked_files": len(indexed),
        "source_commit": lock["source_commit"],
        **totals,
        "research_executed": False,
        "historical_suites_rerun": False,
        "execution_counts_are_not_runtime_validation": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
