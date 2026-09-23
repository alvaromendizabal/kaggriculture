"""Record genuine fresh-kernel output evidence, or verify its published identity."""

import argparse
import ast
import json
import os
from pathlib import Path

import nbformat
from kaggriculture_research.notebook_output_policy import output_is_execution_error
from notebook_provenance import migration_record

from kaggriculture_research.artifacts import digest, file_digest, write_json


def verify(root: Path, record: bool = False) -> dict:
    path = root / "notebooks/02_feature_research.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    cells = [c for c in notebook.cells if c.cell_type == "code"]
    if any(c.id.startswith("livestock-") for c in cells):
        # The new receipt checks all current outputs and the preserved ancestor.
        # Never overwrite the archived 23-cell receipt with a 28-cell identity.
        from verify_livestock_notebook import verify as verify_extension

        return verify_extension(root, record=record)
    if len(cells) != 23 or sum(c.id.startswith("supply-") for c in cells) != 6:
        raise ValueError("Expected 17 earlier and six new code cells")
    migration = migration_record(cells[:17])
    if [c.execution_count for c in cells] != list(range(1, 24)):
        raise ValueError("Notebook was not fully executed in a fresh kernel")
    pngs = 0
    for cell in cells:
        ast.parse(cell.source)
        if not cell.metadata.get("execution", {}).get("iopub.execute_input"):
            raise ValueError("Missing actual kernel execution timing")
        for output in cell.outputs:
            if output_is_execution_error(output):
                raise ValueError("Notebook contains execution errors")
            pngs += int("image/png" in output.get("data", {}))
    if pngs != 6:
        raise ValueError("Static figure fallbacks are missing")
    report_path = root / "reports/supply_notebook_execution.json"
    if record:
        result = {
            "notebook_sha256": file_digest(path),
            "code_cells": len(cells),
            "static_png_outputs": pngs,
            "source_sha256": digest([c.source for c in cells]),
            "provenance_cell_migration": migration,
            "execution_environment": "GitHub Actions"
            if os.environ.get("GITHUB_ACTIONS")
            else "local",
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_commit_sha": os.environ.get("GITHUB_SHA"),
            "study_report_sha256": file_digest(root / "reports/supply_research.json"),
            "plot_source_sha256": file_digest(root / "scripts/supply_plots.py"),
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
        if (
            result["source_sha256"] != digest([c.source for c in cells])
            or result["provenance_cell_migration"] != migration
            or result["code_cells"] != len(cells)
            or result["static_png_outputs"] != pngs
            or result["all_cells_executed"] is not True
            or result["errors"] != 0
            or result["plot_source_sha256"] != file_digest(root / "scripts/supply_plots.py")
        ):
            raise ValueError("Notebook execution receipt metadata is inconsistent")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true")
    print(json.dumps(verify(Path(__file__).resolve().parents[1], parser.parse_args().record)))


if __name__ == "__main__":
    main()
