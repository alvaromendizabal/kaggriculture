"""Durable-before-advance recovery gate for staffing research."""

from pathlib import Path
from typing import Protocol

from kaggriculture_research.artifacts import file_digest


class DurableStore(Protocol):
    """Minimal checkpoint-store interface required by the recovery gate."""

    receipt: dict

    def upload(self, path: Path) -> None: ...


def ensure_existing_checkpoints_durable(
    root: Path,
    jobs: list[dict],
    store: DurableStore,
) -> int:
    """Readback-verify every existing episode before another may be created.

    A process can be interrupted after saving a complete local episode but before its
    remote upload finishes. Recovery therefore makes every existing episode durable
    first. Any upload/readback failure raises before the experiment runner can advance.
    """
    verified = 0
    for job in jobs:
        path = root / job["path"]
        if not path.exists():
            continue
        store.upload(path)
        relative = path.relative_to(root).as_posix()
        receipt = store.receipt["artifacts"].get(relative, {})
        if receipt.get("sha256") != file_digest(path) or not receipt.get("readback_verified"):
            raise ValueError("Existing staffing checkpoint is not durably readback-verified")
        verified += 1

    progress = root / "reports/staffing_progress.json"
    if progress.exists():
        store.upload(progress)
    return verified
