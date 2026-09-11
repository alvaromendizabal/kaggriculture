"""Recovery tests for the staffing pilot's durable-before-advance gate."""

import hashlib
from pathlib import Path

import pytest

from scripts.run_staffing_research import ensure_existing_checkpoints_durable


class FakeStore:
    def __init__(self, root: Path, fail_on: str | None = None) -> None:
        self.root = root
        self.fail_on = fail_on
        self.receipt = {"artifacts": {}}
        self.uploaded: list[str] = []

    def upload(self, path: Path) -> None:
        relative = path.relative_to(self.root).as_posix()
        self.uploaded.append(relative)
        if relative == self.fail_on:
            raise RuntimeError("simulated durable upload failure")
        content = path.read_bytes()
        self.receipt["artifacts"][relative] = {
            "sha256": hashlib.sha256(content).hexdigest(),
            "readback_verified": True,
        }


def test_existing_checkpoints_are_verified_before_advancing(tmp_path):
    first = tmp_path / "artifacts/staffing_episodes/first.json.gz"
    second = tmp_path / "artifacts/staffing_episodes/second.json.gz"
    first.parent.mkdir(parents=True)
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    progress = tmp_path / "reports/staffing_progress.json"
    progress.parent.mkdir(parents=True)
    progress.write_text("{}")
    jobs = [{"path": first.relative_to(tmp_path).as_posix()}, {"path": second.relative_to(tmp_path).as_posix()}]
    store = FakeStore(tmp_path)

    verified = ensure_existing_checkpoints_durable(tmp_path, jobs, store)

    assert verified == 2
    assert store.uploaded == [
        "artifacts/staffing_episodes/first.json.gz",
        "artifacts/staffing_episodes/second.json.gz",
        "reports/staffing_progress.json",
    ]


def test_failed_durable_upload_stops_before_later_checkpoint(tmp_path):
    first = tmp_path / "artifacts/staffing_episodes/first.json.gz"
    second = tmp_path / "artifacts/staffing_episodes/second.json.gz"
    first.parent.mkdir(parents=True)
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    jobs = [{"path": first.relative_to(tmp_path).as_posix()}, {"path": second.relative_to(tmp_path).as_posix()}]
    store = FakeStore(tmp_path, fail_on="artifacts/staffing_episodes/first.json.gz")

    with pytest.raises(RuntimeError, match="simulated durable upload failure"):
        ensure_existing_checkpoints_durable(tmp_path, jobs, store)

    assert store.uploaded == ["artifacts/staffing_episodes/first.json.gz"]
