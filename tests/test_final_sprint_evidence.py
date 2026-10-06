"""Regression tests for published-evidence consistency, including stale plot outputs."""

from __future__ import annotations

import base64
import copy
import importlib.util
import json
import struct
import subprocess
import sys
from pathlib import Path

import nbformat
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "final_sprint_verifier", ROOT / "scripts/verify_final_sprint.py"
)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


@pytest.fixture
def report():
    return json.loads((ROOT / verifier.REPORT_PATH).read_text())


def _notebook(report):
    """Synthetic notebook fixture; not a research execution receipt."""
    milestones = report["milestones"]
    development = milestones["ladder_alignment"]["development"]
    eligible = {
        name: item
        for name, item in development.items()
        if "rescued_keeper_losses" in item and "sacrificed_keeper_wins" in item
    }
    plots = [
        {
            "data": [
                {
                    "type": "bar",
                    "x": list(milestones),
                    "y": [
                        item.get(
                            "new_official_engine_games", item.get("branch_and_calibration_games", 0)
                        )
                        for item in milestones.values()
                    ],
                }
            ],
            "layout": {"width": 1000, "height": 500},
        },
        {
            "data": [
                {
                    "type": "scatter",
                    "text": list(eligible),
                    "x": [item["sacrificed_keeper_wins"] for item in eligible.values()],
                    "y": [item["rescued_keeper_losses"] for item in eligible.values()],
                    "marker": {"size": [item["score_rate"] for item in eligible.values()]},
                }
            ],
            "layout": {"width": 900, "height": 520},
        },
    ]
    cells = [nbformat.v4.new_code_cell("pass", execution_count=1)]
    for index, figure in enumerate(plots, 2):
        output = nbformat.v4.new_output(
            "display_data",
            data={
                "application/vnd.plotly.v1+json": figure,
                "image/svg+xml": '<svg xmlns="http://www.w3.org/2000/svg"><text>fixture</text></svg>',
            },
        )
        cells.append(nbformat.v4.new_code_cell("pass", execution_count=index, outputs=[output]))
    return nbformat.v4.new_notebook(cells=cells)


def _scatter(notebook):
    return notebook.cells[2].outputs[0].data["application/vnd.plotly.v1+json"]["data"][0]


def test_archived_report_is_arithmetically_consistent(report):
    verifier.validate_report(report)
    verifier.validate_notebook(_notebook(report), report)


def test_published_notebook_matches_aggregate_evidence(report):
    verifier.validate_notebook(nbformat.read(ROOT / verifier.NOTEBOOK_PATH, as_version=4), report)


@pytest.mark.parametrize("cell_index", [1, 2])
def test_each_plot_requires_a_saved_svg_fallback(report, cell_index):
    notebook = _notebook(report)
    del notebook.cells[cell_index].outputs[0].data["image/svg+xml"]
    with pytest.raises(ValueError, match="nonempty SVG fallback"):
        verifier.validate_notebook(notebook, report)


@pytest.mark.parametrize(
    "mutation",
    [
        "outcome_count",
        "rate",
        "gap",
        "ledger",
        "cost",
        "reuse",
        "failure_relabel",
        "nonfinite",
        "negative_count",
    ],
)
def test_inconsistent_evidence_is_rejected(report, mutation):
    if mutation == "outcome_count":
        report["validation_alignment"]["recent_keeper_losses"] -= 1
    elif mutation == "rate":
        report["validation_alignment"]["recent_keeper_score_rate"] = 0.99
    elif mutation == "gap":
        report["latest_snapshot"]["gap_to_highest_returned"] = 0
    elif mutation == "ledger":
        report["project_ledger"]["successful_intended_runs"] += 1
    elif mutation == "cost":
        report["project_ledger"]["tracked_active_compute_usd"] += 1
    elif mutation == "reuse":
        report["milestones"]["boundary_rule_cv"]["reused_branch_results"] -= 1
    elif mutation == "failure_relabel":
        report["milestones"]["native_harvest_transport_failure"]["scientific_decision"] = "REJECTED"
    elif mutation == "nonfinite":
        report["milestones"]["frontier_routes"]["keeper_screen_score"] = float("nan")
    else:
        report["milestones"]["late_layer_ablation"]["new_official_engine_games"] = -1
    with pytest.raises(ValueError):
        verifier.validate_report(report)


def test_missing_policy_diagnostics_cannot_be_invented(report):
    notebook = _notebook(report)
    trace = _scatter(notebook)
    trace["text"].append("v38_smarter_feed")
    trace["x"].append(9)
    trace["y"].append(0)
    trace["marker"]["size"].append(0.0416666667)
    with pytest.raises(ValueError, match="missing diagnostics"):
        verifier.validate_notebook(notebook, report)


def test_marker_percentages_cannot_replace_source_scores(report):
    notebook = _notebook(report)
    trace = _scatter(notebook)
    trace["marker"]["size"] = [value * 100 for value in trace["marker"]["size"]]
    with pytest.raises(ValueError, match="marker size"):
        verifier.validate_notebook(notebook, report)


def test_saved_rescue_coordinates_must_match_report(report):
    notebook = _notebook(report)
    _scatter(notebook)["y"][0] += 1
    with pytest.raises(ValueError, match="Saved rescues"):
        verifier.validate_notebook(notebook, report)


def test_plotly_binary_arrays_are_checked(report):
    notebook = _notebook(report)
    trace = _scatter(notebook)
    for key in ("x", "y"):
        values = trace[key]
        trace[key] = {"dtype": "i1", "bdata": base64.b64encode(bytes(values)).decode()}
    sizes = trace["marker"]["size"]
    trace["marker"]["size"] = {
        "dtype": "f8",
        "bdata": base64.b64encode(struct.pack("<3d", *sizes)).decode(),
    }
    verifier.validate_notebook(notebook, report)


def test_execution_errors_and_incomplete_cells_fail(report):
    notebook = _notebook(report)
    notebook.cells[1].execution_count = None
    with pytest.raises(ValueError, match="fully executed"):
        verifier.validate_notebook(notebook, report)
    notebook = _notebook(report)
    notebook.cells[0].outputs = [
        nbformat.v4.new_output("error", ename="ValueError", evalue="broken", traceback=[])
    ]
    with pytest.raises(ValueError, match="cell error"):
        verifier.validate_notebook(notebook, report)


def test_optimized_python_does_not_disable_evidence_checks(report, tmp_path):
    bad_report = copy.deepcopy(report)
    bad_report["project_ledger"]["attempts"] += 1
    (tmp_path / "reports").mkdir()
    (tmp_path / "notebooks").mkdir()
    (tmp_path / verifier.REPORT_PATH).write_text(json.dumps(bad_report))
    nbformat.write(_notebook(report), tmp_path / verifier.NOTEBOOK_PATH)
    script = (
        "import runpy, sys; from pathlib import Path; "
        "module=runpy.run_path(sys.argv[1]); module['verify'](Path(sys.argv[2]))"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-O",
            "-c",
            script,
            str(ROOT / "scripts/verify_final_sprint.py"),
            str(tmp_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Execution ledger mismatch" in result.stderr
