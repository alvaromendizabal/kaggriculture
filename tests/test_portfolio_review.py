"""Guard persisted evidence against stale inputs and missing reviewer-visible figures."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from kaggriculture_research.portfolio import evidence_summary

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "portfolio_verifier", ROOT / "scripts/verify_portfolio_review.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Portfolio verifier could not be imported")
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


@pytest.fixture
def notebook() -> dict:
    return json.loads((ROOT / "notebooks/57_portfolio_review.ipynb").read_text())


def test_committed_review_has_executed_charts_and_matching_evidence(notebook: dict) -> None:
    result = verifier.verify_notebook(notebook)
    assert result["code_cells"] == 4
    assert result["plotly_figures"] == 2


def test_old_input_fingerprint_is_rejected(notebook: dict) -> None:
    hashes = notebook["metadata"]["kaggriculture_portfolio"]["input_sha256"]
    hashes["reports/final_sprint_2026-09-30.json"] = "0" * 64
    with pytest.raises(ValueError, match="STALE_INPUT_HASHES"):
        verifier.verify_notebook(notebook)


def test_changed_code_without_reexecution_is_rejected(notebook: dict) -> None:
    cell = next(cell for cell in notebook["cells"] if cell["cell_type"] == "code")
    cell["source"] = verifier.source_text(cell) + "\nprint('changed source')"
    with pytest.raises(ValueError, match="STALE_CODE_HASH"):
        verifier.verify_notebook(notebook)


@pytest.mark.parametrize(
    ("mime", "error"),
    [
        ("image/svg+xml", "MISSING_SVG_FALLBACK"),
        ("application/vnd.plotly.v1+json", "PLOTLY_FIGURE_COUNT"),
    ],
)
def test_missing_chart_representation_is_rejected(notebook: dict, mime: str, error: str) -> None:
    output = next(
        output
        for cell in notebook["cells"]
        for output in cell.get("outputs", [])
        if "application/vnd.plotly.v1+json" in output.get("data", {})
    )
    del output["data"][mime]
    with pytest.raises(ValueError, match=error):
        verifier.verify_notebook(notebook)


def test_saved_chart_with_wrong_values_is_rejected(notebook: dict) -> None:
    output = next(
        output
        for cell in notebook["cells"]
        for output in cell.get("outputs", [])
        if "application/vnd.plotly.v1+json" in output.get("data", {})
    )
    output["data"]["application/vnd.plotly.v1+json"]["data"][0]["x"][0] = 1.0
    with pytest.raises(ValueError, match="CHART_VALUE_MISMATCH"):
        verifier.verify_notebook(notebook)


def test_impossible_execution_ledger_is_rejected() -> None:
    report = json.loads((ROOT / "reports/final_sprint_2026-09-30.json").read_text())
    changed = copy.deepcopy(report)
    changed["project_ledger"]["attempts"] += 1
    with pytest.raises(ValueError, match="ATTEMPT_TOTAL"):
        evidence_summary(changed)
