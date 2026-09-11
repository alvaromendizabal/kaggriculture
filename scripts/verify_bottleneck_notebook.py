"""Verify the committed decision-feature notebook without running cells or games."""

import hashlib
import json
from pathlib import Path

import nbformat


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root: Path) -> dict:
    """Check byte provenance, fresh-kernel execution, figures and research scope."""
    receipt = json.loads((root / "reports/bottleneck_notebook_execution.json").read_text())
    relative = "notebooks/04_decision_bottlenecks.ipynb"
    if receipt.get("notebook") != relative:
        raise ValueError("Unexpected notebook path in receipt")
    path = root / relative
    report_path = root / "reports/bottleneck_research.json"
    if file_sha256(path) != receipt.get("notebook_sha256"):
        raise ValueError("Notebook bytes differ from the execution receipt")
    if file_sha256(report_path) != receipt.get("report_sha256"):
        raise ValueError("Research report differs from the executed notebook input")
    report = json.loads(report_path.read_text())
    expected = {
        "observations": 161,
        "base_assignment_parity_states": 161,
        "new_games": 0,
        "final_selected_features": 0,
        "official_metric_effect_measured": False,
        "validation_or_holdout_used": False,
        "original_pilot_status": "HALTED_LATENCY_LIMIT",
        "feature_completion_gate": "open_research",
    }
    if any(report.get(key) != value for key, value in expected.items()):
        raise ValueError("Research scope differs from the saved-observation audit")
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    if len(cells) != 4 or [c.execution_count for c in cells] != list(range(1, 5)):
        raise ValueError("Expected four cells executed in a fresh kernel")
    if any(not c.metadata.get("execution", {}).get("iopub.execute_input") for c in cells):
        raise ValueError("Notebook lacks actual per-cell execution timestamps")
    outputs = [out for cell in cells for out in cell.outputs]
    if any(out.output_type == "error" for out in outputs):
        raise ValueError("Notebook contains an error output")
    pngs = sum("image/png" in out.get("data", {}) for out in outputs)
    plots = sum("application/vnd.plotly.v1+json" in out.get("data", {}) for out in outputs)
    checks = {
        "all_cells_executed": True,
        "code_cells": 4,
        "errors": 0,
        "static_png_outputs": pngs,
        "plotly_outputs": plots,
    }
    if pngs != 2 or plots != 2 or any(receipt.get(k) != v for k, v in checks.items()):
        raise ValueError("Figure or execution counts disagree with the receipt")
    return {"status": "PASSED", "new_games": 0, "notebook": relative, **checks}


if __name__ == "__main__":
    print(json.dumps(verify(Path(__file__).resolve().parents[1]), sort_keys=True))
