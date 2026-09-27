"""Genuine execution receipt for the terminal extension; preserve all ancestor evidence."""

import argparse
import ast
import json
import os
from pathlib import Path

import nbformat
from build_terminal_notebook import PRIOR_SOURCE

from kaggriculture_research.artifacts import digest, file_digest, write_json

PRIOR_RECEIPT = "18e258a6f3efb83bac4ea9dc0e2d5ac8e256e260ce0a9e1a36ccf0f996136b22"

KNOWN_KAGGLE_ENGINE_STDERR = (
    "Warning! The implementation of 'quoridor' has known issues. "
    "Please see the games list on github or the code for details."
)


def _allowed_stderr(output) -> bool:
    """Allow only the pinned engine's known import-time quoridor warning."""

    text = output.get("text", "")
    if isinstance(text, list):
        text = "".join(text)
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    return bool(lines) and all(line == KNOWN_KAGGLE_ENGINE_STDERR for line in lines)


def verify(root: Path, record: bool = False) -> dict:
    path = root / "notebooks/02_feature_research.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    cells = [c for c in notebook.cells if c.cell_type == "code"]
    if len(cells) != 32 or sum(c.id.startswith("terminal-") for c in cells) != 4:
        raise ValueError("Expected 28 preserved and four terminal code cells")
    if digest([c.source for c in cells[:28]]) != PRIOR_SOURCE:
        raise ValueError("Earlier source changed")
    prior = root / "reports/livestock_notebook_execution.json"
    if file_digest(prior) != PRIOR_RECEIPT:
        raise ValueError("Archived livestock execution receipt changed")
    ancestor = json.loads(prior.read_text())
    if ancestor["study_report_sha256"] != file_digest(root / "reports/livestock_research.json"):
        raise ValueError("Earlier research evidence changed")
    if ancestor["plot_source_sha256"] != file_digest(root / "scripts/livestock_plots.py"):
        raise ValueError("Earlier plotting source changed")
    if [c.execution_count for c in cells] != list(range(1, 33)):
        raise ValueError("Notebook lacks fresh-kernel execution")
    pngs = 0
    for cell in cells:
        ast.parse(cell.source)
        if not cell.metadata.get("execution", {}).get("iopub.execute_input"):
            raise ValueError("Missing actual kernel timing")
        for output in cell.outputs:
            if output.output_type == "error":
                raise ValueError("Notebook execution contains errors")
            if (
                output.output_type == "stream"
                and output.name == "stderr"
                and not _allowed_stderr(output)
            ):
                raise ValueError("Notebook execution contains unexpected stderr")
            pngs += int("image/png" in output.get("data", {}))
    if pngs != 10:
        raise ValueError("Static figure fallback missing")
    evidence = {
        "notebook_sha256": file_digest(path),
        "code_cells": 32,
        "static_png_outputs": 10,
        "source_sha256": digest([c.source for c in cells]),
        "preserved_earlier_source_sha256": PRIOR_SOURCE,
        "archived_ancestor_receipt_sha256": PRIOR_RECEIPT,
        "ancestor_notebook_sha256": ancestor["notebook_sha256"],
        "study_report_sha256": file_digest(root / "reports/terminal_research.json"),
        "plot_source_sha256": file_digest(root / "scripts/terminal_plots.py"),
        "all_cells_executed": True,
        "errors": 0,
    }
    receipt = root / "reports/terminal_notebook_execution.json"
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
        write_json(receipt, evidence)
        return evidence
    saved = json.loads(receipt.read_text())
    if any(saved.get(k) != v for k, v in evidence.items()):
        raise ValueError("Published notebook differs from execution receipt")
    return saved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true")
    print(json.dumps(verify(Path(__file__).resolve().parents[1], parser.parse_args().record)))


if __name__ == "__main__":
    main()
