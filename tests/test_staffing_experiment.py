"""Registered pilot, recovery and causal-attribution tests for staffing research."""

import json
from pathlib import Path

import pytest

from kaggriculture_research.artifacts import load_checkpoint, save_checkpoint
from kaggriculture_staffing.experiment import (
    episode_hash,
    job_plan,
    run_activation_preflight,
    run_game,
    validate_episode,
)

ROOT = Path(__file__).resolve().parents[1]


def protocol() -> dict:
    return json.loads((ROOT / "configs/staffing_research.json").read_text())


def test_job_plan_is_exact_unique_and_development_only():
    registered = protocol()
    _, jobs = job_plan(ROOT, registered)
    assert len(jobs) == registered["max_games"] == 8
    assert len({job["path"] for job in jobs}) == 8
    assert {job["key"]["seed"] for job in jobs} == {1601, 1602}
    assert {job["key"]["arm"] for job in jobs} == {"sequential", "coordinated"}


def test_real_activation_preflight_reaches_multiple_workers():
    result = run_activation_preflight(protocol()["preflight_seed"])
    assert result["outcome_recorded"] is False
    assert result["multiworker_callbacks"] >= 1
    assert result["maximum_active_workers"] >= 2
    assert result["policy_latency_ms"]["max"] <= protocol()["maximum_policy_latency_ms"]


@pytest.fixture(scope="module")
def paired_games():
    sequential = run_game(1601, 0, "livestock_fertilizer", "sequential")
    coordinated = run_game(1601, 0, "livestock_fertilizer", "coordinated")
    return sequential, coordinated


def test_registered_pair_is_identical_before_terminal_intervention(paired_games):
    sequential, coordinated = paired_games
    assert sequential["preterminal_sha256"] == coordinated["preterminal_sha256"]
    assert sequential["summary"]["terminal_multiworker_callbacks"] >= 1
    assert coordinated["summary"]["terminal_multiworker_callbacks"] >= 1


def test_registered_pair_has_valid_feature_and_transition_evidence(paired_games):
    for payload in paired_games:
        key = {name: payload["summary"][name] for name in ("seed", "seat", "opponent", "arm")}
        validate_episode(payload, key)
        assert payload["semantic_sha256"] == episode_hash(payload)
        assert payload["accounting"]["transitions"] == 1438
        assert len(payload["feature_samples"]) == 23
        assert payload["summary"]["policy_latency_max_ms"] <= protocol()["maximum_policy_latency_ms"]


def test_checkpoint_recovery_reuses_matching_lineage(tmp_path, paired_games):
    payload = paired_games[0]
    lineage = {"registered": "staffing", "seed": 1601, "arm": "sequential"}
    path = tmp_path / "staffing.json.gz"
    save_checkpoint(path, lineage, payload)
    restored = load_checkpoint(path, lineage)
    assert restored["semantic_sha256"] == payload["semantic_sha256"]
    assert load_checkpoint(path, {**lineage, "arm": "coordinated"}) is None
