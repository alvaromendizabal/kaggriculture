"""Review utilities must not alter the identity of registered historical studies."""

import json
from pathlib import Path

import pytest

from kaggriculture_livestock.experiment import common_lineage as livestock_lineage
from kaggriculture_terminal.experiment import common_lineage as terminal_lineage

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("study", "lineage"),
    [("livestock", livestock_lineage), ("terminal", terminal_lineage)],
)
def test_review_package_preserves_registered_experiment_identity(study, lineage):
    protocol = json.loads((ROOT / "configs" / f"{study}_research.json").read_text())
    registration = json.loads((ROOT / "reports" / f"{study}_registration.json").read_text())
    assert lineage(ROOT, protocol) == registration["identity"]["lineage"]
