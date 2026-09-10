"""Operational adapter: skip already uploaded byte-identical games without decoding them.

Registered simulation, policies, features and audit are unchanged. At most two
new games or 60 seconds before starting the next; persist before every upload.
"""

import argparse
import json
import time
from pathlib import Path

from run_terminal_research import register, upload_callback

from kaggriculture_research.artifacts import (
    file_digest,
    load_checkpoint,
    save_checkpoint,
    write_json,
)
from kaggriculture_research.progress import Progress
from kaggriculture_terminal.experiment import job_plan, run_game, validate_episode


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uploads", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/terminal_research.json").read_text())
    register(root, protocol)
    _, jobs = job_plan(root, protocol)
    receipt = json.loads((root / "reports/terminal_uploads.json").read_text())
    for relative in ("reports/terminal_registration.json", "artifacts/terminal_source.zip"):
        if receipt["artifacts"].get(relative, {}).get("sha256") != file_digest(root / relative):
            raise ValueError("Durable source and registration required")
    ready = upload_callback(root, args.uploads)
    completed = new = 0
    started = time.monotonic()
    progress = Progress()
    for job in jobs:
        path = root / job["path"]
        prior = receipt["artifacts"].get(job["path"])
        if prior is not None:
            if not path.exists() or file_digest(path) != prior["sha256"]:
                raise ValueError("Restore missing/changed completed game before resuming")
            completed += 1
            continue
        if new >= 2 or time.monotonic() - started >= 60:
            break
        payload = load_checkpoint(path, job["lineage"])
        if payload is None:
            if path.exists():
                raise ValueError("Existing checkpoint lineage differs")
            with progress.stage("terminal_" + "_".join(map(str, job["key"].values()))):
                payload = run_game(**job["key"])
                save_checkpoint(path, job["lineage"], payload)
            new += 1
        validate_episode(payload, job["key"])
        ready(path)
        completed += 1
    result = {
        "complete": completed == 48,
        "completed_games": completed,
        "new_games": new,
        "source_sha256": file_digest(Path(__file__)),
        "max_new_games": 2,
        "resume_scope": "uploaded byte-identical games reused; independent audit unchanged",
    }
    write_json(root / "reports/terminal_slice_progress.json", result)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
