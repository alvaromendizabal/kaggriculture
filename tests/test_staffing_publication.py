"""Check publication honesty and tamper detection without simulating games."""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "staffing_verifier", ROOT / "scripts/verify_staffing_audit.py"
)
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def test_actual_evidence_passes():
    report = VERIFIER.evidence(ROOT)
    assert report["feature_evidence"]["observations"] == 161


@pytest.mark.parametrize(
    "field,value",
    [
        ("accepted_games", 8),
        ("published_eight_game_score", 1.0),
        ("validation_or_holdout_used", True),
        ("new_games_run", 1),
        ("registration_caveat", ""),
    ],
)
def test_unjustified_publication_claims_fail(tmp_path, field, value):
    (tmp_path / "reports").mkdir()
    for name in VERIFIER.INPUTS:
        shutil.copy2(ROOT / name, tmp_path / name)
    path = tmp_path / VERIFIER.INPUTS[0]
    report = json.loads(path.read_text())
    report[field] = value
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        VERIFIER.evidence(tmp_path)


def test_changed_remote_evidence_is_rejected(tmp_path):
    (tmp_path / "reports").mkdir()
    for name in VERIFIER.INPUTS:
        shutil.copy2(ROOT / name, tmp_path / name)
    path = tmp_path / VERIFIER.INPUTS[1]
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="differs from the S3"):
        VERIFIER.evidence(tmp_path)
