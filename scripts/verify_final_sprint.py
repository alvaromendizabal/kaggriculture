from __future__ import annotations

import json
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
report = json.loads((ROOT / "reports" / "final_sprint_2026-09-30.json").read_text())

required = {
    "late_layer_ablation": "REJECTED_SCREEN",
    "onpolicy_population": "TRAINING_REJECTED",
    "frontier_routes": "SCREEN_REJECTED",
    "public_adaptive_frontier": "SCREEN_REJECTED",
    "ladder_alignment": "NO_FIXED_POLICY_IMPROVEMENT",
    "boundary_selector": "INNER_VALIDATION_REJECTED",
    "boundary_rule_cv": "ROLLING_CV_REJECTED",
}
for name, decision in required.items():
    item = report["milestones"][name]
    assert item["status"] == "COMPLETED", (name, item["status"])
    assert item["decision"] == decision, (name, item["decision"])

harvest = report["milestones"]["native_harvest_transport_failure"]
assert harvest["status"] == "FAILED"
assert harvest["category"] == "MODEL"
assert harvest["new_submissions"] == 0

notebook_path = ROOT / "notebooks" / "56_final_sprint_ladder_alignment.ipynb"
notebook = nbformat.read(notebook_path, as_version=4)
code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
assert code_cells and all(cell.execution_count is not None for cell in code_cells)

errors = [
    output
    for cell in code_cells
    for output in cell.outputs
    if output.output_type == "error"
]
plotly = sum(
    "application/vnd.plotly.v1+json" in output.get("data", {})
    for cell in code_cells
    for output in cell.outputs
)
assert not errors
assert plotly == 2
print("final-sprint evidence: PASS")
