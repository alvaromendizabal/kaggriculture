"""Acceptance checks for the self-contained, noncompetitive reviewer example."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "run_demo.py"
SPEC = importlib.util.spec_from_file_location("kaggriculture_public_demo", DEMO)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Demo module could not be loaded")
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)


def test_higher_score_does_not_hide_sacrificed_wins() -> None:
    result = demo.run_demo()
    development = result["development"]
    assert development["keeper_score_rate"] == pytest.approx(0.5)
    assert development["candidate_score_rate"] == pytest.approx(2 / 3)
    assert development["metrics"]["net_score_units"] == 1.0
    assert development["metrics"]["rescues"] == 3
    assert development["metrics"]["sacrifices"] == 2
    assert development["accepted"] is False
    assert development["decision"] == "REJECTED_SACRIFICED_WINS"


def test_future_episodes_are_reserved_without_candidate_outcomes() -> None:
    chronology = demo.run_demo()["chronology"]
    development = set(chronology["development_ids"])
    holdout = set(chronology["reserved_holdout_ids"])
    assert len(development) == 6
    assert len(holdout) == 2
    assert development.isdisjoint(holdout)
    assert {row.episode_id for row in demo.TOY_CANDIDATE} == development
    assert chronology["candidate_evaluated_on_holdout"] is False


def test_invalid_episode_pairs_are_rejected() -> None:
    guards = demo.run_demo()["rejected_invalid_inputs"]
    assert guards == {
        "duplicate_keeper": "DUPLICATE_EPISODE_ID",
        "duplicate_candidate": "DUPLICATE_EPISODE_ID",
        "misaligned_candidate": "EPISODE_ALIGNMENT",
    }


@pytest.mark.parametrize("optimize", [False, True])
def test_cli_runs_from_unrelated_directory_without_result_files(
    tmp_path: Path, optimize: bool
) -> None:
    command = [sys.executable]
    if optimize:
        command.append("-O")
    command.append(str(DEMO))
    result = subprocess.run(
        command,
        cwd=tmp_path,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    report = json.loads(result.stdout)
    assert "synthetic" in report["scope"]
    assert report["development"]["accepted"] is False
    assert report == demo.run_demo()
    assert result.stderr == ""
    assert list(tmp_path.iterdir()) == []
