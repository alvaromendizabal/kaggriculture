"""Execute aggregate review notebooks; no competitive games, training, or cloud access."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_portfolio_review import code_hash, input_hashes, verify_notebook  # noqa: E402


def build_portfolio_notebook() -> nbformat.NotebookNode:
    markdown = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    notebook = nbformat.v4.new_notebook(
        cells=[
            markdown(
                "# Kaggriculture: when local agent strength failed to transfer\n\n"
                "**Alvaro Mendizabal · Agent evaluation · Simulation · AWS/SageMaker**\n\n"
                "This executed review reads committed aggregate evidence dated **September 30, "
                "2026**. It runs no competition games or private models. Re-execution checks "
                "the published record and a fictional evaluation example; it does not "
                "independently reproduce a leaderboard score.\n\n"
                "The key contribution was recognizing that a saturated fixed opponent panel "
                "overstated live strength and changing the evaluation protocol. "
                "[Case study](../CASE_STUDY.md) · "
                "[Reproducibility](../docs/REPRODUCIBILITY.md) · "
                "[Detailed sprint](56_final_sprint_ladder_alignment.ipynb)"
            ),
            code(
                """
import json
import sys
from pathlib import Path

from IPython.display import display

ROOT = Path.cwd()
if not (ROOT / "reports").is_dir():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))
from run_demo import run_demo  # noqa: E402

from kaggriculture_research.portfolio import chart_bundle, evidence_summary  # noqa: E402

report = json.loads((ROOT / "reports/final_sprint_2026-09-30.json").read_text())
summary = evidence_summary(report)
print("Evidence cutoff:", summary["observed_utc"])
print("Scope: saved aggregate evidence; no new games, training, or submissions.")
""".strip()
            ),
            markdown(
                "## Correct the validator before promoting a policy\n\n"
                "Exact keeper replay reconstructed **18 wins, 10 ties, and 20 losses** across "
                "48 recorded ladder episodes: **47.9% win/tie score**. Below, all fixed "
                "alternatives scored worse than the keeper on the older 24 development "
                "episodes. These percentages are not official leaderboard ratings.\n\n"
                "Chronological separation and fresh responsive-opponent safety are separate "
                "gates: a recorded opponent tape cannot react to changed actions. "
                "Earlier promotion claims based on the saturated panel need reconsideration."
            ),
            code(
                """
display(chart_bundle(summary, "development"), raw=True)
""".strip()
            ),
            markdown(
                "## Keep negative experiments and operational failures distinct\n\n"
                "The historical ledger records **43 successful executions, 28 execution "
                "failures, and 4 controlled stops**, totaling 75 attempts. A correctly "
                "executed negative experiment counts as a successful execution.\n\n"
                "These totals are inherited from the September record; this notebook "
                "execution does not add a research attempt. The native harvest/service "
                "mechanism remained scientifically unresolved after a diagnostics error. "
                "The archived active-compute estimate is not an account-wide AWS bill."
            ),
            code(
                """
display(chart_bundle(summary, "ledger"), raw=True)
""".strip()
            ),
            markdown(
                "## A runnable example: higher average score can still fail the gate\n\n"
                "The following fictional six-episode comparison raises score from 50% to "
                "66.7%, rescuing three losses while sacrificing two incumbent wins. Its "
                "explicit toy gate permits at most one sacrificed win, so it rejects the "
                "candidate. Two later fictional episodes stay reserved. The example also "
                "checks that duplicate or misaligned episode IDs are rejected.\n\n"
                "These authored toy outcomes are not competition measurements or a private "
                "policy recipe. The structured output also binds the plotted summaries to "
                "the committed report for verification after saving and reopening."
            ),
            code(
                """
toy = run_demo()
evidence = {"project": summary, "synthetic_demo": toy}
print("Synthetic decision:", toy["development"]["decision"])
print("PORTFOLIO_EVIDENCE_JSON " + json.dumps(evidence, sort_keys=True, allow_nan=False))
""".strip()
            ),
            markdown(
                "## Competitive outcome and limits\n\n"
                "The report records keeper **1691.0**, another active slot **1516.2**, and "
                "a highest returned leaderboard row of **3084.1**. The export was paginated, "
                "so that last number is not verified exhaustive rank one. The dated keeper "
                "gap is **1393.1**; no improvement is claimed from this publication.\n\n"
                "The historical outcome ledger separately records **2048.7** for an earlier "
                "returned submission outside that latest-two pair. The repository does not "
                "claim a new best or a completed competitive recovery experiment.\n\n"
                "Project-authored work includes observation safety, reference integration, "
                "paired evaluation, chronology, recovery, and promotion controls. "
                "[External controllers retain attribution]"
                "(../docs/research/leading_solution_reproduction_matrix.md). Private data, "
                "checkpoints, submission archives, and exact current competitive "
                "orchestration remain outside this review."
            ),
        ],
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        },
    )
    for index, cell in enumerate(notebook.cells):
        cell["id"] = f"portfolio-{index:02d}"
    return notebook


def execute_inprocess(notebook: nbformat.NotebookNode) -> None:
    """Execute real IPython cells and capture their actual rich displays and stdout."""
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.utils.capture import capture_output

    shell = InteractiveShell.instance()
    shell.reset(new_session=True)
    count = 0
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        count += 1
        with capture_output(stdout=True, stderr=True, display=True) as captured:
            result = shell.run_cell(cell.source, store_history=True)
        if result.error_before_exec or result.error_in_exec:
            raise RuntimeError(f"Notebook cell {count} failed: {captured.stdout} {captured.stderr}")
        cell.execution_count = count
        cell.outputs = []
        if captured.stdout:
            cell.outputs.append(
                nbformat.v4.new_output("stream", name="stdout", text=captured.stdout)
            )
        if captured.stderr:
            cell.outputs.append(
                nbformat.v4.new_output("stream", name="stderr", text=captured.stderr)
            )
        for output in captured.outputs:
            cell.outputs.append(
                nbformat.v4.new_output("display_data", data=output.data, metadata=output.metadata)
            )


def execute(notebook: nbformat.NotebookNode, engine: str) -> None:
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.execution_count = None
            cell.outputs = []
    if engine == "inprocess":
        execute_inprocess(notebook)
    else:
        manager = KernelManager(kernel_name="python3")
        manager.kernel_spec.argv = [
            sys.executable,
            "-m",
            "ipykernel_launcher",
            "-f",
            "{connection_file}",
        ]
        NotebookClient(
            notebook,
            km=manager,
            timeout=120,
            kernel_name="python3",
            resources={"metadata": {"path": str(ROOT)}},
            allow_errors=False,
        ).execute()


def main() -> None:
    import os

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=("jupyter", "inprocess"), default="jupyter")
    parser.add_argument("--notebook", choices=("56", "57", "both"), default="both")
    parser.add_argument(
        "--publish", action="store_true", help="Replace the canonical saved notebooks"
    )
    args = parser.parse_args()
    os.chdir(ROOT)
    destination = ROOT / ("notebooks" if args.publish else "artifacts/portfolio-review")
    destination.mkdir(parents=True, exist_ok=True)
    paths = []
    if args.notebook in {"56", "both"}:
        paths.append("56_final_sprint_ladder_alignment.ipynb")
    if args.notebook in {"57", "both"}:
        paths.append("57_portfolio_review.ipynb")
    for name in paths:
        notebook = (
            build_portfolio_notebook()
            if name.startswith("57")
            else nbformat.read(ROOT / "notebooks" / name, as_version=4)
        )
        execute(notebook, args.engine)
        notebook.metadata["kaggriculture_execution"] = {
            "engine": args.engine,
            "executed_utc": datetime.now(UTC).isoformat(),
            "scope": "committed aggregate reports and synthetic data only",
            "python": ".".join(map(str, sys.version_info[:3])),
        }
        if name.startswith("57"):
            notebook.metadata["kaggriculture_portfolio"] = {
                "schema_version": 1,
                "engine": args.engine,
                "input_sha256": input_hashes(),
                "code_sha256": code_hash(notebook),
            }
            verify_notebook(notebook)
        else:
            cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
            if not cells or any(cell.execution_count is None for cell in cells):
                raise ValueError("UNEXECUTED_SPRINT_NOTEBOOK")
            if any(output.output_type == "error" for cell in cells for output in cell.outputs):
                raise ValueError("SPRINT_NOTEBOOK_ERROR")
        path = destination / name
        temporary = path.with_suffix(".ipynb.tmp")
        nbformat.write(notebook, temporary)
        reopened = nbformat.read(temporary, as_version=4)
        nbformat.validate(reopened)
        if name.startswith("57"):
            verify_notebook(reopened)
        temporary.replace(path)
        print(f"Executed and reopened: {path.relative_to(ROOT)}; engine={args.engine}")


if __name__ == "__main__":
    main()
