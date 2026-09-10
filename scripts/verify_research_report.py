"""Verify published evidence without rerunning an unchanged 80-game experiment.

Full simulator runs and notebook execution occur before publication on AWS. CI
independently runs mechanics/determinism tests, checks source and protocol lineage,
recomputes paired statistics from all 80 public outcome rows, and validates the
executed notebook. Raw trajectory checkpoints remain private in S3.
"""

import ast
import json
from itertools import product
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd

from kaggriculture_research.artifacts import digest, file_digest
from kaggriculture_research.environment import engine_manifest
from kaggriculture_research.experiment import paired_summary


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    report = json.loads((root / "reports/feature_research.json").read_text())
    protocol = json.loads((root / "configs/feature_research.json").read_text())
    if digest(protocol) != report["protocol_sha256"] or protocol != report["lineage"]["protocol"]:
        raise ValueError("Report protocol differs from the registered experiment")
    if engine_manifest() != report["lineage"]["engine"]:
        raise ValueError("Report engine differs from the pinned installation")
    for name, sha in report["lineage"]["code"].items():
        if file_digest(root / "src/kaggriculture_research" / name) != sha:
            raise ValueError(f"Report is stale for {name}")
    frame = pd.read_csv(root / "reports/feature_games.csv")
    columns = ["seed", "seat", "opponent", "variant"]
    expected = set(
        product(
            protocol["development_seeds"],
            protocol["seats"],
            protocol["opponents"],
            protocol["variants"],
        )
    )
    if len(frame) != 80 or set(frame[columns].itertuples(index=False, name=None)) != expected:
        raise ValueError("Incomplete or duplicated paired design")
    if report["validation_or_holdout_used"] or report["feature_completion_gate"] != "closed":
        raise ValueError("Research boundary changed")
    computed = paired_summary(frame, protocol["bootstrap_resamples"], protocol["bootstrap_seed"])
    pd.testing.assert_frame_equal(
        computed,
        pd.DataFrame(report["paired_results"]),
        check_dtype=False,
        check_like=True,
        atol=1e-9,
        rtol=0,
    )
    pd.testing.assert_frame_equal(
        computed,
        pd.read_csv(root / "reports/feature_ablations.csv"),
        check_dtype=False,
        atol=1e-9,
        rtol=0,
    )
    if not np.isfinite(frame.select_dtypes(include="number").to_numpy()).all():
        raise ValueError("Non-finite outcome")
    behavior = pd.read_csv(root / "reports/feature_behavior.csv")
    joined = frame.merge(behavior, on=columns, validate="one_to_one")
    if (
        len(joined) != 80
        or not (
            joined.harvested_units
            == joined.sold_units + joined.unsold_product_units + joined.discarded_units
        ).all()
    ):
        raise ValueError("Published product conservation failed")
    audit = json.loads((root / "reports/feature_behavior_audit.json").read_text())
    if file_digest(root / "scripts/audit_feature_behavior.py") != audit["audit_code_sha256"]:
        raise ValueError("Behavior audit source changed")
    notebook = nbformat.read(root / "notebooks/02_feature_research.ipynb", as_version=4)
    cloud = json.loads((root / "reports/cloud_verification.json").read_text())
    recorded = next(
        a for a in cloud["run"]["artifacts"] if a["path"] == "notebooks/02_feature_research.ipynb"
    )
    if file_digest(root / recorded["path"]) != recorded["sha256"]:
        raise ValueError("Notebook differs from its executed AWS artifact")
    nbformat.validate(notebook)
    cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    if len(cells) != 7:
        raise ValueError("Unexpected research notebook structure")
    for cell in cells:
        ast.parse(cell.source)
        if cell.execution_count is None:
            raise ValueError("Research notebook has an unexecuted cell")
        if any(
            o.output_type == "error" or (o.output_type == "stream" and o.name == "stderr")
            for o in cell.outputs
        ):
            raise ValueError("Research notebook contains execution errors")
    print("Verified lineage, 80 paired outcomes, uncertainty, conservation and executed notebook.")


if __name__ == "__main__":
    main()
