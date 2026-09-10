"""A new execution receipt for the extended notebook; preserve its ancestor receipt."""

import argparse
import ast
import json
import os
from pathlib import Path

import nbformat
from notebook_provenance import migration_record

from kaggriculture_research.artifacts import digest, file_digest, write_json

PRIOR_SOURCE = "aaf0381fa1aa2f9a216bbe49e5f1b7348a304fd612ba73ef28301473ba7a3d0a"
PRIOR_RECEIPT = "628e850d094f07a2429bedc3bddb8b3ef67d02ca947e71c74e62e3bebba80d0b"


def verify(root: Path, record: bool = False) -> dict:
    path = root / "notebooks/02_feature_research.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    cells = [c for c in notebook.cells if c.cell_type == "code"]
    if len(cells) != 28 or sum(c.id.startswith("livestock-") for c in cells) != 5:
        raise ValueError("Expected 23 preserved and five new code cells")
    if digest([c.source for c in cells[:23]]) != PRIOR_SOURCE:
        raise ValueError("Earlier code source changed")
    ancestor_path = root / "reports/supply_notebook_execution.json"
    ancestor = json.loads(ancestor_path.read_text())
    if file_digest(ancestor_path) != PRIOR_RECEIPT:
        raise ValueError("Archived execution receipt was altered")
    if ancestor["provenance_cell_migration"] != migration_record(cells[:17]):
        raise ValueError("Earlier provenance adapter changed")
    if ancestor["study_report_sha256"] != file_digest(
        root / "reports/supply_research.json"
    ) or ancestor["plot_source_sha256"] != file_digest(root / "scripts/supply_plots.py"):
        raise ValueError("Earlier evidence changed")
    if [c.execution_count for c in cells] != list(range(1, 29)):
        raise ValueError("Notebook was not executed in a fresh kernel")
    pngs = 0
    for cell in cells:
        ast.parse(cell.source)
        if not cell.metadata.get("execution", {}).get("iopub.execute_input"):
            raise ValueError("Missing actual kernel timing")
        for output in cell.outputs:
            if output.output_type == "error" or (
                output.output_type == "stream" and output.name == "stderr"
            ):
                raise ValueError("Execution contains errors")
            pngs += int("image/png" in output.get("data", {}))
    if pngs != 8:
        raise ValueError("Static plot fallbacks are missing")
    evidence = {
        "notebook_sha256": file_digest(path),
        "code_cells": len(cells),
        "static_png_outputs": pngs,
        "source_sha256": digest([c.source for c in cells]),
        "preserved_earlier_source_sha256": PRIOR_SOURCE,
        "archived_ancestor_receipt_sha256": PRIOR_RECEIPT,
        "ancestor_notebook_sha256": ancestor["notebook_sha256"],
        "preservation_scope": "first_23_code_sources; new whole-notebook execution identity",
        "study_report_sha256": file_digest(root / "reports/livestock_research.json"),
        "plot_source_sha256": file_digest(root / "scripts/livestock_plots.py"),
        "all_cells_executed": True,
        "errors": 0,
    }
    receipt_path = root / "reports/livestock_notebook_execution.json"
    if record:
        evidence.update(
            {
                "execution_environment": "GitHub Actions"
                if os.environ.get("GITHUB_ACTIONS")
                else "local",
                "github_run_id": os.environ.get("GITHUB_RUN_ID"),
                "github_commit_sha": os.environ.get("GITHUB_SHA"),
            }
        )
        write_json(receipt_path, evidence)
        return evidence
    result = json.loads(receipt_path.read_text())
    if any(result.get(k) != v for k, v in evidence.items()):
        raise ValueError("Published notebook differs from its execution receipt")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true")
    print(json.dumps(verify(Path(__file__).resolve().parents[1], parser.parse_args().record)))
