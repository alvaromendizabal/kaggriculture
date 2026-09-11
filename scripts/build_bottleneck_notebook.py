"""Build and genuinely execute the measured decision-bottleneck notebook."""

import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from textwrap import dedent

import nbformat
from nbclient import NotebookClient


def main():
    root = Path(__file__).resolve().parents[1]
    report_path = root / "reports/bottleneck_research.json"
    report = json.loads(report_path.read_text())
    if report["observations"] != 161 or report["official_metric_effect_measured"]:
        raise ValueError("Expected saved-observation evidence, not a claimed policy win")

    def markdown(text):
        return nbformat.v4.new_markdown_cell(dedent(text).strip())

    def code(text):
        return nbformat.v4.new_code_cell(dedent(text).strip())

    cells = [
        markdown("""
            # Decision bottlenecks
            ## Which constraint is costing the joint plan?
            This is a **saved-observation feature experiment**, not a new match evaluation.
            The staffing pilot stopped at seven accepted games when game eight exceeded
            its latency limit. No result is invented for that game.

            The representation measures exact conditional utility losses from removing a
            worker or harvest, changing storage room, or taking the runner-up plan.
            All comparisons use the same bounded legal route menu. Feature research is open.
            """),
        code("""
            %matplotlib inline
            from pathlib import Path
            import json
            import pandas as pd
            import matplotlib.pyplot as plt
            import plotly.express as px
            import plotly.io as pio
            from IPython.display import display

            pio.renderers.default = 'plotly_mimetype'
            ROOT = Path.cwd() if (Path.cwd() / 'reports').exists() else Path.cwd().parent
            report = json.loads((ROOT / 'reports/bottleneck_research.json').read_text())
            assert report['base_assignment_parity_states'] == report['observations'] == 161
            assert report['new_games'] == 0 and report['final_selected_features'] == 0
            display(pd.DataFrame([{
                'Saved observations': report['observations'],
                'Descriptor columns': report['candidate_columns'],
                'Varying': report['varying_columns'],
                'Constant': report['constant_columns'],
                'Selected for a final model': 0,
            }]))
            """),
        markdown("""
            ## Marginal worker value
            A removal value is the best retained-menu utility lost when that worker is
            forced to PASS. This is **not hiring ROI**: it omits future production, an
            alternative starting location, and the hire price. A worker can have zero
            removal value when another worker can collect the same resource.
            Rows below are explored development groups, not independent validation folds.
            """),
        code("""
            groups = pd.DataFrame(report['group_means'])
            groups['group'] = (
                groups['seed'].astype(str) + ' / seat ' + groups['seat'].astype(str)
                + ' / ' + groups['arm']
            )
            worker_cols = [f'bottleneck.worker{i}_removal_loss' for i in range(4)]
            worker_values = groups.set_index('group')[worker_cols]
            worker_values.columns = ['Farmer', 'Hand 1', 'Hand 2', 'Hand 3']
            fig = px.imshow(
                worker_values, text_auto='.1f', aspect='auto',
                labels={'x': 'Worker forced to PASS', 'y': 'Group', 'color': 'Utility loss'},
                title='Conditional worker-removal value', width=1050, height=520,
            )
            display(fig)
            fig_static, ax = plt.subplots(figsize=(10, 5))
            image = ax.imshow(worker_values.to_numpy(), aspect='auto')
            ax.set_xticks(range(4), worker_values.columns)
            ax.set_yticks(range(len(worker_values)), worker_values.index)
            ax.set_title('Conditional worker-removal value | static review')
            fig_static.colorbar(image, ax=ax, label='Utility loss')
            fig_static.tight_layout()
            plt.show()
            """),
        markdown("""
            ## Coverage is a gate, not proof of feature value
            The 39 columns include context and availability controls. Count constants and
            redundancy instead of calling every generated column a novel predictive signal.
            The original study has incomplete, latency-censored outcomes.
            This audit measures no change in official match score.
            """),
        code("""
            coverage = pd.Series({
                'Varying': report['varying_columns'],
                'Constant': report['constant_columns'],
            }, name='Columns')
            fig = px.bar(
                x=coverage.index, y=coverage.values,
                labels={'x': 'Observed coverage', 'y': 'Descriptor columns'},
                title='Representation coverage on 161 saved states', width=800, height=400,
            )
            display(fig)
            fig_static, ax = plt.subplots(figsize=(7, 3.8))
            ax.bar(coverage.index, coverage.values)
            ax.set_ylabel('Descriptor columns')
            ax.set_title('Observed coverage | not feature-selection evidence')
            fig_static.tight_layout()
            plt.show()
            timings = pd.DataFrame([report['latency_including_menu_ms']])
            display(timings.rename_axis('Extraction latency (ms)'))
            """),
        markdown("""
            ## Decision and next controlled test
            Keep feature research open. Use the observed worker and harvest bottlenecks to
            prioritize option-selection ablations while holding staffing and market rules
            equal between arms. Fit any learned threshold/ranker on development episode
            groups only. Confirm on fresh development seeds and unrelated opponents before
            untouched evaluation. Do not expand a family merely to increase column counts.

            The current top leaderboard rating could not be retrieved in this session.
            This representation is not claimed to beat that unverified rating.

            **Sources:** `docs/bottleneck_research.md`, pinned route/game semantics, and
            the exact source identities in the following execution record.
            """),
        code("""
            display(pd.DataFrame([{
                'Source commit': report['source_commit'],
                'Original registration': report['registration_identity_sha256'],
                'Original pilot': report['original_pilot_status'],
                'Feature gate': report['feature_completion_gate'],
            }]))
            for limitation in report['limitations']:
                print('- ' + limitation)
            """),
    ]
    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata.kernelspec = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    NotebookClient(
        notebook, timeout=90, kernel_name="python3", resources={"metadata": {"path": str(root)}}
    ).execute()
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    outputs = [output for cell in code_cells for output in cell.outputs]
    if any(output.output_type == "error" for output in outputs):
        raise ValueError("Notebook execution produced an error")
    if any(cell.execution_count is None for cell in code_cells):
        raise ValueError("Unexecuted code cell")
    pngs = sum("image/png" in output.get("data", {}) for output in outputs)
    plots = sum("application/vnd.plotly.v1+json" in output.get("data", {}) for output in outputs)
    if pngs < 2 or plots < 2:
        raise ValueError("Both Plotly figures and static figure fallbacks are required")
    path = root / "notebooks/04_decision_bottlenecks.ipynb"
    path.parent.mkdir(exist_ok=True)
    nbformat.write(notebook, path)
    environment = "GitHub Actions" if os.environ.get("GITHUB_ACTIONS") else "Local verification"
    if Path.home() == Path("/home/sagemaker-user"):
        environment = "AWS SageMaker"
    receipt = {
        "notebook": path.relative_to(root).as_posix(),
        "all_cells_executed": True,
        "code_cells": len(code_cells),
        "errors": 0,
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "environment": environment,
        "static_png_outputs": pngs,
        "plotly_outputs": plots,
        "repository_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "notebook_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    destination = root / "reports/bottleneck_notebook_execution.json"
    destination.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
