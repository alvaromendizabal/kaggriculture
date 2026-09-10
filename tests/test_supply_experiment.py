"""Protocol, paired-inference and completed-episode recovery tests."""

import copy
import gzip
import json
import runpy
from pathlib import Path

import pandas as pd
import pytest

from kaggriculture_research.artifacts import save_checkpoint
from kaggriculture_research.progress import Progress
from kaggriculture_research.supply_experiment import (
    ARMS,
    CONTRASTS,
    METRICS,
    OPPONENTS,
    common_lineage,
    episode_hash,
    job_plan,
    paired_summary,
    run_batch,
    run_game,
    validate_episode,
)

ROOT = Path(__file__).resolve().parents[1]


def test_supply_protocol_boundaries():
    protocol = json.loads((ROOT / "configs/supply_research.json").read_text())
    common, jobs = job_plan(ROOT, protocol)
    assert len(jobs) == len({j["path"] for j in jobs}) == 64
    assert common["protocol"] == protocol
    for field, value in (
        ("development_seeds", [2101, 1302, 1303, 1304]),
        ("rival_scenario_weight", 0.6),
        ("max_games", 65),
    ):
        modified = {**protocol, field: value}
        with pytest.raises(ValueError):
            common_lineage(ROOT, modified)


def test_paired_clusters_keep_seats_and_opponents_together():
    frame = pd.DataFrame(
        [
            {
                "seed": seed,
                "seat": seat,
                "opponent": opponent,
                "arm": arm,
                **{metric: seed + seat + list(ARMS).index(arm) for metric in METRICS},
            }
            for seed in (1, 2, 3, 4)
            for seat in (0, 1)
            for opponent in OPPONENTS
            for arm in ARMS
        ]
    )
    result = paired_summary(frame, 100, 0)
    for treatment, control in CONTRASTS:
        expected = list(ARMS).index(treatment) - list(ARMS).index(control)
        rows = result[result.contrast == treatment + "-" + control]
        assert (rows.effect == expected).all() and (rows.seed_clusters == 4).all()
    for invalid in (frame.iloc[:-1], pd.concat([frame, frame.iloc[:1]])):
        with pytest.raises(ValueError):
            paired_summary(invalid, 100, 0)


@pytest.fixture(scope="module")
def fixture_episode():
    # Mechanism-test seed, never part of the research/validation/holdout pools.
    return run_game(53, 0, "market10", "cash")


def test_supply_episode_integrity_and_reproducible_callback_restore(fixture_episode):
    payload = fixture_episode
    key = {k: payload["summary"][k] for k in ("seed", "seat", "opponent", "arm")}
    validate_episode(payload, key)
    assert payload["summary"]["state_roundtrips"] == 31
    assert len(payload["feature_samples"]) == 181
    altered = copy.deepcopy(payload)
    altered["records"].pop()
    altered["semantic_sha256"] = episode_hash(altered)
    with pytest.raises(ValueError, match="callback sequence"):
        validate_episode(altered, key)


def test_supply_resume_reuses_verified_episode_and_never_runs_it_again(
    tmp_path, monkeypatch, fixture_episode
):
    import kaggriculture_research.supply_experiment as module

    payload = fixture_episode
    key = {k: payload["summary"][k] for k in ("seed", "seat", "opponent", "arm")}
    lineage, relative = {"fixture": True}, "artifacts/supply_episodes/fixture.json.gz"
    save_checkpoint(tmp_path / relative, lineage, payload)
    monkeypatch.setattr(
        module, "job_plan", lambda *args: ({}, [{"key": key, "lineage": lineage, "path": relative}])
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("A valid completed game must not rerun")

    monkeypatch.setattr(module, "run_game", forbidden)
    result = run_batch(tmp_path, {"experiment": "fixture"}, Progress())
    assert result["complete"] and result["new_games"] == 0 and result["reused_games"] == 1
    envelope = json.loads(gzip.decompress((tmp_path / relative).read_bytes()))
    envelope["payload"]["summary"]["coins"] += 1
    (tmp_path / relative).write_bytes(gzip.compress(json.dumps(envelope).encode()))
    with pytest.raises(ValueError, match="checksum mismatch"):
        run_batch(tmp_path, {"experiment": "fixture"}, Progress())


def test_remote_restore_validates_before_installing(tmp_path, monkeypatch, fixture_episode):
    import io
    import urllib.request

    restore = runpy.run_path(str(ROOT / "scripts/restore_supply_checkpoints.py"))["restore_job"]
    key = {k: fixture_episode["summary"][k] for k in ("seed", "seat", "opponent", "arm")}
    job = {"key": key, "lineage": {"fixture": True}, "path": "artifacts/episode.json.gz"}
    source = tmp_path / "remote.json.gz"
    save_checkpoint(source, job["lineage"], fixture_episode)
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: io.BytesIO(source.read_bytes()))
    assert restore(tmp_path, job, "https://authorized.invalid/checkpoint")
    assert not restore(tmp_path, job, None)
    outside = {**job, "path": "../outside.json.gz"}
    with pytest.raises(ValueError, match="escapes"):
        restore(tmp_path, outside, "https://authorized.invalid/checkpoint")
    wrong = {**job, "path": "artifacts/other.json.gz", "lineage": {"fixture": False}}
    with pytest.raises(ValueError, match="lineage differs"):
        restore(tmp_path, wrong, "https://authorized.invalid/checkpoint")
    assert not (tmp_path / wrong["path"]).exists()
