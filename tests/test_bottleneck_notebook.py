"""Tamper tests use synthetic notebook fixtures, never pretend research execution."""

import hashlib
import json
import runpy
from pathlib import Path

import nbformat
import pytest

VERIFY = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/verify_bottleneck_notebook.py")
)["verify"]


def write_fixture(root, edit_notebook=None, edit_report=None):
    (root / "notebooks").mkdir()
    (root / "reports").mkdir()
    report = {
        "observations": 161, "base_assignment_parity_states": 161,
        "new_games": 0, "final_selected_features": 0,
        "official_metric_effect_measured": False, "validation_or_holdout_used": False,
        "original_pilot_status": "HALTED_LATENCY_LIMIT", "feature_completion_gate": "open_research",
    }
    if edit_report:
        report.update(edit_report)
    cells = []
    for index in range(1, 5):
        cell = nbformat.v4.new_code_cell("# Synthetic verifier-test fixture only")
        cell.execution_count = index
        cell.metadata["execution"] = {"iopub.execute_input": "synthetic-test-timestamp"}
        if index in (2, 3):
            cell.outputs = [nbformat.v4.new_output(
                "display_data",
                data={"image/png": "AA==", "application/vnd.plotly.v1+json": {"data": []}},
            )]
        cells.append(cell)
    notebook = nbformat.v4.new_notebook(cells=cells)
    if edit_notebook:
        edit_notebook(notebook)
    path = root / "notebooks/04_decision_bottlenecks.ipynb"
    nbformat.write(notebook, path)
    report_path = root / "reports/bottleneck_research.json"
    report_path.write_text(json.dumps(report))
    receipt = {
        "notebook": "notebooks/04_decision_bottlenecks.ipynb", "all_cells_executed": True,
        "code_cells": 4, "errors": 0, "static_png_outputs": 2, "plotly_outputs": 2,
        "notebook_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
    }
    (root / "reports/bottleneck_notebook_execution.json").write_text(json.dumps(receipt))


def test_synthetic_valid_contract(tmp_path):
    write_fixture(tmp_path)
    assert VERIFY(tmp_path)["status"] == "PASSED"


@pytest.mark.parametrize("path", [
    "notebooks/04_decision_bottlenecks.ipynb", "reports/bottleneck_research.json",
])
def test_byte_tampering_rejected(tmp_path, path):
    write_fixture(tmp_path)
    target = tmp_path / path
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ValueError, match="differ"):
        VERIFY(tmp_path)


@pytest.mark.parametrize("scope", [
    {"new_games": 1}, {"validation_or_holdout_used": True},
    {"official_metric_effect_measured": True}, {"final_selected_features": 1},
    {"original_pilot_status": "COMPLETE"}, {"feature_completion_gate": "closed"},
])
def test_no_relabeling_of_audit_as_score_or_final_selection(tmp_path, scope):
    write_fixture(tmp_path, edit_report=scope)
    with pytest.raises(ValueError, match="scope"):
        VERIFY(tmp_path)


def test_unexecuted_cell_rejected_even_with_updated_file_hash(tmp_path):
    write_fixture(tmp_path, edit_notebook=lambda nb: nb.cells[1].update(execution_count=None))
    with pytest.raises(ValueError, match="fresh kernel"):
        VERIFY(tmp_path)


def test_missing_kernel_timestamp_rejected(tmp_path):
    write_fixture(tmp_path, edit_notebook=lambda nb: nb.cells[0].metadata.clear())
    with pytest.raises(ValueError, match="timestamps"):
        VERIFY(tmp_path)


def test_missing_plotly_fallback_rejected(tmp_path):
    write_fixture(tmp_path, edit_notebook=lambda nb: nb.cells[1].outputs.clear())
    with pytest.raises(ValueError, match="Figure"):
        VERIFY(tmp_path)


def test_error_output_rejected(tmp_path):
    def add_error(nb):
        nb.cells[0].outputs.append(nbformat.v4.new_output(
            "error", ename="ValueError", evalue="synthetic test", traceback=[]
        ))
    write_fixture(tmp_path, edit_notebook=add_error)
    with pytest.raises(ValueError, match="error output"):
        VERIFY(tmp_path)


def test_committed_notebook_integration():
    root = Path(__file__).resolve().parents[1]
    assert (root / "reports/bottleneck_research.json").is_file()
    assert VERIFY(root)["status"] == "PASSED"
