"""Record genuine fresh-kernel output evidence, or verify its published identity."""

import argparse
import ast
import json
import os
from pathlib import Path

import nbformat

from kaggriculture_research.artifacts import digest, file_digest, write_json


def verify(root: Path, record: bool = False) -> dict:
    path = root / "notebooks/02_feature_research.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    cells = [c for c in notebook.cells if c.cell_type == "code"]
    if len(cells) != 23 or sum(c.id.startswith("supply-") for c in cells) != 6:
        raise ValueError("Expected 17 preserved and six new code cells")
    if digest([c.source for c in cells[:17]]) != (
        "45952532e959648cb3bbc79adb8a55aa39eaab68549532790babb520ed6f14ff"
    ):
        raise ValueError("Earlier research notebook source changed")
    if [c.execution_count for c in cells] != list(range(1, 24)):
        raise ValueError("Notebook was not fully executed in a fresh kernel")
    pngs = 0
    for cell in cells:
        ast.parse(cell.source)
        if not cell.metadata.get("execution", {}).get("iopub.execute_input"):
            raise ValueError("Missing actual kernel execution timing")
        for output in cell.outputs:
            if output.output_type == "error" or (
                output.output_type == "stream" and output.name == "stderr"
            ):
                raise ValueError("Notebook contains execution errors")
            pngs += int("image/png" in output.get("data", {}))
    if pngs < 5:
        raise ValueError("Static figure fallbacks are missing")
    report_path = root / "reports/supply_notebook_execution.json"
    if record:
        result = {
            "notebook_sha256": file_digest(path),
            "code_cells": len(cells),
            "static_png_outputs": pngs,
            "source_sha256": digest([c.source for c in cells]),
            "preserved_first17_source_sha256": digest([c.source for c in cells[:17]]),
            "execution_environment": "GitHub Actions"
            if os.environ.get("GITHUB_ACTIONS")
            else "local",
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_commit_sha": os.environ.get("GITHUB_SHA"),
            "study_report_sha256": file_digest(root / "reports/supply_research.json"),
            "all_cells_executed": True,
            "errors": 0,
        }
        write_json(report_path, result)
    else:
        result = json.loads(report_path.read_text())
        if result["notebook_sha256"] != file_digest(path) or result[
            "study_report_sha256"
        ] != file_digest(root / "reports/supply_research.json"):
            raise ValueError("Published notebook differs from its execution receipt")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true")
    print(json.dumps(verify(Path(__file__).resolve().parents[1], parser.parse_args().record)))


if __name__ == "__main__":
    main()
