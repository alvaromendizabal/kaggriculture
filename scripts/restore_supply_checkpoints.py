"""Restore authorized missing study checkpoints; reject corruption before installation."""

import argparse
import json
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from kaggriculture_research.artifacts import load_checkpoint, write_atomic
from kaggriculture_research.supply_experiment import job_plan, validate_episode


def restore_job(root: Path, job: dict, download_url: str | None) -> bool:
    path = (root / job["path"]).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Checkpoint target escapes the project")
    if path.exists():
        payload = load_checkpoint(path, job["lineage"])
        if payload is None:
            raise ValueError("Existing checkpoint lineage differs; do not overwrite")
        validate_episode(payload, job["key"])
        return False
    if not download_url:
        raise ValueError("No authorized download URL for this missing checkpoint")
    try:
        with urllib.request.urlopen(download_url, timeout=60) as response:
            content = response.read()
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Checkpoint download stopped: HTTP {error.code}") from None
    except urllib.error.URLError:
        raise RuntimeError("Checkpoint download unavailable") from None
    with tempfile.TemporaryDirectory(prefix="supply-restore-") as temporary:
        candidate = Path(temporary) / "episode.json.gz"
        write_atomic(candidate, content)
        payload = load_checkpoint(candidate, job["lineage"])
        if payload is None:
            raise ValueError("Downloaded checkpoint lineage differs")
        validate_episode(payload, job["key"])
    write_atomic(path, content)
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--downloads", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/supply_research.json").read_text())
    _, jobs = job_plan(root, protocol)
    downloads = json.loads(args.downloads.read_text())["downloads"]
    expected = {j["path"] for j in jobs}
    if set(downloads) - expected:
        raise ValueError("Download manifest includes an unregistered target")
    restored = reused = 0
    for job in jobs:
        if job["path"] not in downloads and not (root / job["path"]).exists():
            continue
        if restore_job(root, job, downloads.get(job["path"])):
            restored += 1
        else:
            reused += 1
    print(
        json.dumps(
            {"restored_games": restored, "verified_existing_games": reused, "games_executed": 0}
        )
    )


if __name__ == "__main__":
    main()
