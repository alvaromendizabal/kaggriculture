"""Verify halted-study evidence and its genuinely executed publication notebook."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import nbformat
import pandas as pd

INPUTS = (
    "reports/staffing_audit_summary.json",
    "reports/staffing_observed_games.csv",
    "reports/staffing_feature_coverage.csv",
)
NOTEBOOK = "notebooks/03_staffing_research.ipynb"
RECEIPT = "reports/staffing_notebook_execution.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence(root: Path) -> dict:
    report = json.loads((root / INPUTS[0]).read_text())
    if (
        report["status"] != "HALTED_LATENCY_LIMIT"
        or report["accepted_games"] != 7
        or report["expected_games"] != 8
        or report["published_eight_game_score"] is not None
        or report["new_games_run"] != 0
        or report["validation_or_holdout_used"]
        or report["feature_completion_gate"] != "open_research"
    ):
        raise ValueError("Halted pilot scope was changed")
    for relative, item in report["evidence_files"].items():
        path = root / relative
        if sha(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise ValueError("Published evidence differs from the S3 audit")
    games = pd.read_csv(root / INPUTS[1])
    coverage = pd.read_csv(root / INPUTS[2])
    keys = ["seed", "seat", "arm", "opponent"]
    if len(games) != 7 or games.duplicated(keys).any():
        raise ValueError("Accepted game identities are incomplete or duplicated")
    expected = {
        (seed, seat, arm, "livestock_fertilizer")
        for seed in (1601, 1602)
        for seat in (0, 1)
        for arm in ("sequential", "coordinated")
    }
    missing = expected - set(games[keys].itertuples(index=False, name=None))
    if missing != {(1602, 1, "coordinated", "livestock_fertilizer")}:
        raise ValueError("Unexpected missing game")
    if len(coverage) != 53 or coverage.feature.duplicated().any():
        raise ValueError("Feature registry drift")
    if int((coverage.distinct_values == 1).sum()) != 2:
        raise ValueError("Feature coverage counts changed")
    if not (coverage.status == "provisional_not_predictively_selected").all():
        raise ValueError("Feature selection was not established by this audit")
    if report["feature_evidence"]["selected_for_final_model"] != 0:
        raise ValueError("Unsupported feature selection claim")
    if not report.get("registration_caveat"):
        raise ValueError("Prior CI exposure caveat is missing")
    failed = report["failed_attempt"]
    if failed["outcome"] is not None or failed["maximum_latency_ms"] is not None:
        raise ValueError("Unsaved rejected-game values cannot be reconstructed")
    indexed = games.set_index(keys)
    pairs = report["completed_pairs"]
    if len(pairs) != 3 or len({(p["seed"], p["seat"]) for p in pairs}) != 3:
        raise ValueError("Completed pair count drift")
    for pair in pairs:
        if not pair["identical_preterminal"]:
            raise ValueError("Causal prefix mismatch")
        base = (pair["seed"], pair["seat"])
        for metric in ("coin_margin", "match_score"):
            delta = (
                indexed.loc[(*base, "coordinated", "livestock_fertilizer"), metric]
                - indexed.loc[(*base, "sequential", "livestock_fertilizer"), metric]
            )
            if float(delta) != pair[metric + "_difference"]:
                raise ValueError("Paired evidence differs from observed games")
    candidate = report["runtime_candidate"]
    if candidate["promoted"] or candidate["feature_vectors_identical"] != 161:
        raise ValueError("Runtime candidate scope changed")
    if candidate["farm_actions_and_diagnostics_identical"] != 69:
        raise ValueError("Snapshot parity count changed")
    return report


def verify(root: Path, record: bool = False) -> dict:
    report = evidence(root)
    path = root / NOTEBOOK
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    if len(cells) != 6 or [cell.execution_count for cell in cells] != list(range(1, 7)):
        raise ValueError("Expected six fresh-kernel executed cells")
    pngs = 0
    for cell in cells:
        ast.parse(cell.source)
        if not cell.metadata.get("execution", {}).get("iopub.execute_input"):
            raise ValueError("Actual kernel timing is missing")
        for output in cell.outputs:
            if output.output_type == "error" or (
                output.output_type == "stream" and output.name == "stderr"
            ):
                raise ValueError("Notebook contains execution errors")
            pngs += int("image/png" in output.get("data", {}))
    if pngs != 3:
        raise ValueError("Expected three static figures")
    result = {
        "notebook": NOTEBOOK,
        "notebook_sha256": sha(path),
        "input_sha256": {name: sha(root / name) for name in INPUTS},
        "builder_sha256": sha(root / "scripts/build_staffing_audit_notebook.py"),
        "code_cells": 6,
        "static_png_outputs": pngs,
        "all_cells_executed": True,
        "errors": 0,
        "accepted_games": report["accepted_games"],
        "published_eight_game_score": None,
    }
    receipt = root / RECEIPT
    if record:
        result.update(
            {
                "executed_at_utc": datetime.now(UTC).isoformat(),
                "execution_environment": "GitHub Actions"
                if os.getenv("GITHUB_ACTIONS")
                else "local",
                "github_run_id": os.getenv("GITHUB_RUN_ID"),
                "github_commit_sha": os.getenv("GITHUB_SHA"),
            }
        )
        receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    else:
        saved = json.loads(receipt.read_text())
        if any(saved.get(key) != value for key, value in result.items()):
            raise ValueError("Notebook publication differs from its execution receipt")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true")
    print(json.dumps(verify(Path(__file__).resolve().parents[1], parser.parse_args().record)))
