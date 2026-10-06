"""Check published aggregate arithmetic and saved figures, without replaying private games."""

from __future__ import annotations

import ast
import base64
import json
import math
import struct
from datetime import datetime
from pathlib import Path
from typing import Any

import nbformat

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = Path("reports/final_sprint_2026-09-30.json")
NOTEBOOK_PATH = Path("notebooks/56_final_sprint_ladder_alignment.ipynb")
REQUIRED_DECISIONS = {
    "late_layer_ablation": "REJECTED_SCREEN",
    "onpolicy_population": "TRAINING_REJECTED",
    "frontier_routes": "SCREEN_REJECTED",
    "public_adaptive_frontier": "SCREEN_REJECTED",
    "ladder_alignment": "NO_FIXED_POLICY_IMPROVEMENT",
    "boundary_selector": "INNER_VALIDATION_REJECTED",
    "boundary_rule_cv": "ROLLING_CV_REJECTED",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _number(value: Any, field: str) -> float:
    _require(type(value) in (int, float), f"{field}: expected a number")
    _require(math.isfinite(value), f"{field}: nonfinite value")
    return float(value)


def _count(value: Any, field: str) -> int:
    _require(type(value) is int and value >= 0, f"{field}: expected a nonnegative integer")
    return value


def _close(actual: Any, expected: float, field: str, tolerance: float = 1e-9) -> None:
    _require(
        math.isclose(_number(actual, field), expected, rel_tol=0.0, abs_tol=tolerance),
        f"{field}: arithmetic mismatch",
    )


def _finite_tree(value: Any) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _finite_tree(item)
    elif isinstance(value, list):
        for item in value:
            _finite_tree(item)
    elif isinstance(value, float):
        _require(math.isfinite(value), "Evidence contains a nonfinite value")


def validate_report(report: dict[str, Any]) -> None:
    """Verify the archived summary's internal consistency, not private source authenticity."""
    _finite_tree(report)
    snapshot = report["latest_snapshot"]
    observed = datetime.fromisoformat(snapshot["observed_utc"].replace("Z", "+00:00"))
    _require(observed.utcoffset() is not None, "Snapshot requires an explicit timezone")
    for key in ("keeper_rating", "second_active_rating", "highest_returned_leaderboard_score"):
        _number(snapshot[key], key)
    _require(snapshot["leaderboard_pagination_present"] is True, "Pagination caveat missing")
    _close(
        snapshot["gap_to_highest_returned"],
        snapshot["highest_returned_leaderboard_score"] - snapshot["keeper_rating"],
        "gap_to_highest_returned",
    )
    _close(
        snapshot["gap_to_stretch_target"],
        _number(snapshot["stretch_target"], "stretch_target") - snapshot["keeper_rating"],
        "gap_to_stretch_target",
    )

    alignment = report["validation_alignment"]
    _require(alignment["status"] == "CORRECTED", "Validator correction missing")
    for prefix, total_key in (
        ("recent_keeper", "recent_keeper_episodes"),
        ("development", "development_episodes"),
    ):
        total = _count(alignment[total_key], total_key)
        counts = [_count(alignment[f"{prefix}_{key}"], key) for key in ("wins", "ties", "losses")]
        _require(total > 0 and sum(counts) == total, f"{prefix}: outcome counts mismatch")
        _close(alignment[f"{prefix}_score_rate"], (counts[0] + 0.5 * counts[1]) / total, prefix)
    _require(
        alignment["development_episodes"] < alignment["recent_keeper_episodes"],
        "Development consumes every recorded episode",
    )

    milestones = report["milestones"]
    _require(
        set(milestones) == set(REQUIRED_DECISIONS) | {"native_harvest_transport_failure"},
        "Milestone set differs from archived research scope",
    )
    for name, decision in REQUIRED_DECISIONS.items():
        item = milestones[name]
        _require(item["status"] == "COMPLETED", f"{name}: execution status mismatch")
        _require(item["decision"] == decision, f"{name}: scientific decision mismatch")
    for name, item in milestones.items():
        _require(_count(item["new_submissions"], name) == 0, f"{name}: unexpected submission")
        for key in (
            "new_official_engine_games",
            "branch_and_calibration_games",
            "reused_branch_results",
            "attempted_development_games",
        ):
            if key in item:
                _count(item[key], f"{name}.{key}")
    harvest = milestones["native_harvest_transport_failure"]
    _require(harvest["status"] == "FAILED", "Native harvest failure was relabeled")
    _require(
        harvest["scientific_decision"] is None, "Execution failure is not a scientific rejection"
    )
    _require(
        report["current_recovery_artifact"]["competitive_run_completed"] is False,
        "Recovery has no completed competitive result in this snapshot",
    )
    ladder = milestones["ladder_alignment"]
    _require(ladder["exact_replay_fidelity_passed"] is True, "Replay fidelity evidence missing")
    keeper = ladder["development"]["keeper"]
    for key in ("wins", "ties", "losses", "score_rate"):
        _close(keeper[key], alignment[f"development_{key}"], f"development.keeper.{key}")
    for name, item in ladder["development"].items():
        rate = _number(item["score_rate"], f"{name}.score_rate")
        _require(0 <= rate <= 1, f"{name}: score is outside [0, 1]")
        for key, maximum in (
            ("rescued_keeper_losses", alignment["development_losses"]),
            ("sacrificed_keeper_wins", alignment["development_wins"]),
        ):
            if key in item:
                _require(_count(item[key], key) <= maximum, f"{name}: impossible {key}")
    _require(
        milestones["boundary_selector"]["branch_and_calibration_games"]
        == milestones["boundary_rule_cv"]["reused_branch_results"],
        "Branch reuse count mismatch",
    )
    _require(
        milestones["boundary_rule_cv"]["new_official_engine_games"] == 0,
        "Rolling CV must reuse prior games",
    )

    ledger = report["project_ledger"]
    categories = (
        "successful_intended_runs",
        "execution_failures",
        "authorization_stops",
        "other_controlled_stops",
    )
    attempts = _count(ledger["attempts"], "attempts")
    _require(sum(_count(ledger[k], k) for k in categories) == attempts, "Execution ledger mismatch")
    costs = [
        _number(ledger[k], k)
        for k in (
            "successful_active_compute_usd",
            "failed_active_compute_usd",
            "stopped_active_compute_usd",
        )
    ]
    _require(all(cost >= 0 for cost in costs), "Negative compute cost")
    # Each of the three categories and the total was independently rounded to four decimals.
    _close(ledger["tracked_active_compute_usd"], sum(costs), "compute total", tolerance=0.0002)


def _array(value: Any) -> list[Any]:
    """Read plain arrays or Plotly's one-dimensional typed-array JSON encoding."""
    if isinstance(value, list):
        return value
    _require(isinstance(value, dict), "Expected Plotly array")
    formats = {
        "i1": "b",
        "u1": "B",
        "i2": "h",
        "u2": "H",
        "i4": "i",
        "u4": "I",
        "i8": "q",
        "u8": "Q",
        "f4": "f",
        "f8": "d",
    }
    dtype = value.get("dtype")
    _require(dtype in formats and "bdata" in value, "Unsupported Plotly array encoding")
    raw = base64.b64decode(value["bdata"], validate=True)
    size = struct.calcsize(formats[dtype])
    _require(len(raw) % size == 0, "Malformed Plotly array bytes")
    result = [item[0] for item in struct.iter_unpack("<" + formats[dtype], raw)]
    if "shape" in value:
        _require(str(value["shape"]) == str(len(result)), "Expected one-dimensional Plotly data")
    return result


def validate_notebook(notebook: Any, report: dict[str, Any]) -> None:
    """Reject stale saved charts, including fabricated values for missing diagnostics."""
    nbformat.validate(notebook)
    cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    _require(len(cells) == 3, "Expected three final-sprint code cells")
    _require(
        [cell.execution_count for cell in cells] == [1, 2, 3], "Notebook is not fully executed"
    )
    figures = []
    for cell in cells:
        ast.parse(cell.source)
        for output in cell.outputs:
            _require(output.output_type != "error", "Notebook has a cell error")
            _require(
                not (output.output_type == "stream" and output.name == "stderr"),
                "Notebook contains stderr",
            )
            plot = output.get("data", {}).get("application/vnd.plotly.v1+json")
            if plot is not None:
                fallback = output.get("data", {}).get("image/svg+xml", "")
                if isinstance(fallback, list):
                    fallback = "".join(fallback)
                _require(
                    isinstance(fallback, str) and bool(fallback.strip()) and "<svg" in fallback,
                    "Plotly figure is missing a nonempty SVG fallback",
                )
                figures.append(plot)
    _require(len(figures) == 2, "Expected two persisted Plotly figures")
    for figure in figures:
        _require(len(figure["data"]) == 1, "Unexpected figure trace count")
        _require(figure["layout"].get("width", 0) >= 700, "Figure width is too small")
        _require(figure["layout"].get("height", 0) >= 400, "Figure height is too small")
    bar = figures[0]["data"][0]
    milestones = report["milestones"]
    _require(
        bar["type"] == "bar" and _array(bar["x"]) == list(milestones), "Milestone labels differ"
    )
    expected_games = [
        item.get("new_official_engine_games", item.get("branch_and_calibration_games", 0))
        for item in milestones.values()
    ]
    _require(_array(bar["y"]) == expected_games, "Saved game-count chart differs from report")
    development = report["milestones"]["ladder_alignment"]["development"]
    eligible = {
        name: item
        for name, item in development.items()
        if name != "keeper" and "rescued_keeper_losses" in item and "sacrificed_keeper_wins" in item
    }
    scatter = figures[1]["data"][0]
    _require(scatter["type"] == "scatter", "Expected rescue scatter plot")
    _require(
        _array(scatter["text"]) == list(eligible),
        "Saved rescue chart includes missing diagnostics or omits reported policies",
    )
    _require(
        _array(scatter["x"]) == [item["sacrificed_keeper_wins"] for item in eligible.values()],
        "Saved sacrifices differ from report",
    )
    _require(
        _array(scatter["y"]) == [item["rescued_keeper_losses"] for item in eligible.values()],
        "Saved rescues differ from report",
    )
    sizes = _array(scatter["marker"]["size"])
    _require(len(sizes) == len(eligible), "Saved marker-size count differs")
    for size, item in zip(sizes, eligible.values(), strict=True):
        _close(size, item["score_rate"], "Saved score marker size")


def verify(root: Path = ROOT) -> dict[str, Any]:
    report = json.loads((root / REPORT_PATH).read_text())
    validate_report(report)
    validate_notebook(nbformat.read(root / NOTEBOOK_PATH, as_version=4), report)
    return {
        "scope": "published aggregate consistency and saved outputs; no private game rerun",
        "milestones": len(report["milestones"]),
        "code_cells": 3,
        "plotly_figures": 2,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
