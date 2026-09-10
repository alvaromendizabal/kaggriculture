"""Public notebook recovery must never imply that unavailable bytes were reread."""

import copy
import hashlib
import runpy
from pathlib import Path

import nbformat
import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPERS = runpy.run_path(str(ROOT / "scripts/notebook_provenance.py"))
verify = HELPERS["verify_private_artifacts"]
archived = HELPERS["archived_study_sources"]


@pytest.fixture
def evidence():
    content = b"private test-only trace"
    artifact = {"path": "artifacts/test.json.gz", "sha256": hashlib.sha256(content).hexdigest()}
    receipt = {
        "run": {
            "status": "completed",
            "steps": [{"status": "passed"}],
            "artifacts": [{**artifact, "bytes": len(content)}],
        },
        "verification": {
            "all_semantic_hashes_verified": True,
            "downloaded_and_sha256_verified_artifacts": 1,
        },
    }
    return content, artifact, receipt


def test_receipt_mode_explicitly_does_not_claim_local_byte_verification(tmp_path, evidence):
    _, artifact, receipt = evidence
    assert verify(tmp_path, [artifact], receipt) == {
        "local_bytes_verified": 0,
        "receipt_only_verified": 1,
    }


def test_direct_mode_reads_and_hashes_existing_bytes(tmp_path, evidence):
    content, artifact, receipt = evidence
    path = tmp_path / artifact["path"]
    path.parent.mkdir()
    path.write_bytes(content)
    assert verify(tmp_path, [artifact], receipt) == {
        "local_bytes_verified": 1,
        "receipt_only_verified": 0,
    }
    path.write_bytes(b"X" * len(content))
    with pytest.raises(ValueError, match="corrupt"):
        verify(tmp_path, [artifact], receipt)


@pytest.mark.parametrize("damage", ["status", "steps", "semantic", "count", "hash", "missing"])
def test_invalid_prior_receipt_fails_closed(tmp_path, evidence, damage):
    _, artifact, receipt = evidence
    if damage == "status":
        receipt["run"]["status"] = "failed"
    elif damage == "steps":
        receipt["run"]["steps"][0]["status"] = "failed"
    elif damage == "semantic":
        receipt["verification"]["all_semantic_hashes_verified"] = False
    elif damage == "count":
        receipt["verification"]["downloaded_and_sha256_verified_artifacts"] = 0
    elif damage == "hash":
        receipt["run"]["artifacts"][0]["sha256"] = "0" * 64
    else:
        receipt.clear()
    with pytest.raises(ValueError):
        verify(tmp_path, [artifact], receipt)


@pytest.mark.parametrize("path", ["../private.json.gz", "/tmp/private.json.gz", "reports/x"])
def test_unsafe_paths_fail(tmp_path, evidence, path):
    _, artifact, receipt = evidence
    artifact["path"] = path
    receipt["run"]["artifacts"][0]["path"] = path
    with pytest.raises(ValueError, match="Unsafe"):
        verify(tmp_path, [artifact], receipt)


def test_symlink_does_not_count_as_missing_private_bytes(tmp_path, evidence):
    _, artifact, receipt = evidence
    path = tmp_path / artifact["path"]
    path.parent.mkdir()
    path.symlink_to(tmp_path / "absent")
    with pytest.raises(ValueError, match="symlink"):
        verify(tmp_path, [artifact], receipt)


def test_duplicate_receipt_paths_fail(tmp_path, evidence):
    _, artifact, receipt = evidence
    receipt["run"]["artifacts"].append(copy.deepcopy(receipt["run"]["artifacts"][0]))
    receipt["verification"]["downloaded_and_sha256_verified_artifacts"] = 2
    with pytest.raises(ValueError, match="Duplicate"):
        verify(tmp_path, [artifact], receipt)


def test_only_declared_provenance_cell_can_change_and_stale_output_is_cleared():
    notebook = nbformat.read(ROOT / "notebooks/02_feature_research.ipynb", as_version=4)
    cells = [c for c in notebook.cells if c.cell_type == "code"][:17]
    cells[6].source = HELPERS["ORIGINAL_CELL"]
    original = archived(cells)
    cells[6].execution_count = 7
    cells[6].outputs = [nbformat.v4.new_output("stream", name="stdout", text="Old verification")]
    HELPERS["migrate_study1_provenance"](cells)
    assert cells[6].execution_count is None and cells[6].outputs == []
    assert archived(cells, require_migration=True) == original
    assert HELPERS["migration_record"](cells)["changed_code_cell_numbers"] == [7]
    cells[3].source += "\n# undeclared edit"
    with pytest.raises(ValueError, match="outside the declared"):
        archived(cells)


def test_undeclared_provenance_replacement_fails():
    notebook = nbformat.read(ROOT / "notebooks/02_feature_research.ipynb", as_version=4)
    cells = [c for c in notebook.cells if c.cell_type == "code"][:17]
    cells[6].source = "print('verified')"
    with pytest.raises(ValueError, match="Undeclared"):
        archived(cells)


def test_perfect_score_labels_do_not_overlap_chart_title(monkeypatch):
    import pandas as pd
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import supply_plots

    captured = []
    make = supply_plots.plt.subplots

    def capture(*args, **kwargs):
        fig, axis = make(*args, **kwargs)
        captured.append((fig, axis))
        return fig, axis

    monkeypatch.setattr(supply_plots.plt, "subplots", capture)
    monkeypatch.setattr(supply_plots, "display", lambda *args, **kwargs: None)
    scores = pd.DataFrame(
        {"market10": [0.5, 0, 1, 1], "relationship101": [0.25, 0, 0.25, 0.25]},
        index=["bank", "visible", "history", "cash"],
    )
    supply_plots.show_match_scores(scores)
    fig, axis = captured[0]
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    renderer = canvas.get_renderer()
    title = axis.title.get_window_extent(renderer)
    assert axis.get_ylim() == (0.0, 1.0)
    assert all(text.get_window_extent(renderer).y1 < title.y0 for text in axis.texts)
