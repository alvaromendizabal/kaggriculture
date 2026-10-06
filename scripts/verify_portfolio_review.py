"""Verify saved aggregate review evidence using only the Python standard library."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaggriculture_research.portfolio import evidence_summary  # noqa: E402

INPUT_FILES = (
    "reports/final_sprint_2026-09-30.json",
    "reports/final_sprint_reproduction_manifest.json",
    "src/kaggriculture_research/final_sprint.py",
    "src/kaggriculture_research/portfolio.py",
    "examples/run_demo.py",
)
MARKER = "PORTFOLIO_EVIDENCE_JSON "


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def input_hashes(root: Path = ROOT) -> dict[str, str]:
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in INPUT_FILES}


def source_text(cell: dict[str, object]) -> str:
    source = cell["source"]
    return "".join(source) if isinstance(source, list) else source


def code_hash(notebook: dict[str, object]) -> str:
    sources = [source_text(cell) for cell in notebook["cells"] if cell["cell_type"] == "code"]
    return hashlib.sha256(json.dumps(sources, ensure_ascii=False).encode()).hexdigest()


def demo_summary(root: Path = ROOT) -> dict[str, object]:
    spec = importlib.util.spec_from_file_location(
        "portfolio_review_demo", root / "examples/run_demo.py"
    )
    require(spec is not None and spec.loader is not None, "DEMO_IMPORT")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run_demo()


def expected_evidence(root: Path = ROOT) -> dict[str, object]:
    report = json.loads((root / "reports/final_sprint_2026-09-30.json").read_text())
    return {"project": evidence_summary(report), "synthetic_demo": demo_summary(root)}


def verify_notebook(notebook: dict[str, object], root: Path = ROOT) -> dict[str, object]:
    metadata = notebook.get("metadata", {}).get("kaggriculture_portfolio", {})
    require(metadata.get("schema_version") == 1, "PORTFOLIO_SCHEMA")
    require(metadata.get("input_sha256") == input_hashes(root), "STALE_INPUT_HASHES")
    require(metadata.get("code_sha256") == code_hash(notebook), "STALE_CODE_HASH")
    require(metadata.get("engine") in {"jupyter", "inprocess"}, "EXECUTION_ENGINE")
    code = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    require(len(code) == 4, "CODE_CELL_COUNT")
    require([cell.get("execution_count") for cell in code] == [1, 2, 3, 4], "EXECUTION_COUNTS")
    figures = []
    summaries = []
    for cell in code:
        require(bool(cell.get("outputs")), "MISSING_SAVED_OUTPUT")
        for output in cell["outputs"]:
            require(output["output_type"] != "error", "NOTEBOOK_ERROR")
            data = output.get("data", {})
            if "application/vnd.plotly.v1+json" in data:
                svg = data.get("image/svg+xml", "")
                svg = "".join(svg) if isinstance(svg, list) else svg
                require("<svg" in svg and "</svg>" in svg, "MISSING_SVG_FALLBACK")
                figures.append(data["application/vnd.plotly.v1+json"])
            if output["output_type"] == "stream":
                content = output["text"]
                content = "".join(content) if isinstance(content, list) else content
                for line in content.splitlines():
                    if line.startswith(MARKER):
                        summaries.append(json.loads(line.removeprefix(MARKER)))
    require(len(figures) == 2, "PLOTLY_FIGURE_COUNT")
    expected = expected_evidence(root)
    require(summaries == [expected], "SAVED_SUMMARY_MISMATCH")
    for figure, key in zip(figures, ("development_score_rates", "execution_counts"), strict=True):
        values = expected["project"][key]
        require(len(figure["data"]) == 1, "CHART_TRACE_COUNT")
        require(figure["data"][0]["y"] == list(values), "CHART_LABEL_MISMATCH")
        require(figure["data"][0]["x"] == list(values.values()), "CHART_VALUE_MISMATCH")
    return {"code_cells": len(code), "plotly_figures": len(figures), "engine": metadata["engine"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--notebook", type=Path, default=ROOT / "notebooks/57_portfolio_review.ipynb"
    )
    args = parser.parse_args()
    result = verify_notebook(json.loads(args.notebook.read_text()))
    print("portfolio review: PASS " + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
