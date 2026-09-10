"""Prepare exactly one registered game, with uploads performed in a separate short call.

This operational adapter avoids long combined compute/transfer sessions. It
requires every preceding game and the source registration to have upload receipts.
It reuses an existing valid pending game and never starts a second pending game.
"""

import json
from pathlib import Path

from run_terminal_research import register

from kaggriculture_research.artifacts import file_digest, load_checkpoint, save_checkpoint
from kaggriculture_research.progress import Progress
from kaggriculture_terminal.experiment import job_plan, run_game, validate_episode


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/terminal_research.json").read_text())
    register(root, protocol)
    _, jobs = job_plan(root, protocol)
    receipt = json.loads((root / "reports/terminal_uploads.json").read_text())
    for relative in ("reports/terminal_registration.json", "artifacts/terminal_source.zip"):
        if receipt["artifacts"].get(relative, {}).get("sha256") != file_digest(root / relative):
            raise ValueError("Durable source and registration required")
    for job in jobs:
        path = root / job["path"]
        prior = receipt["artifacts"].get(job["path"])
        if prior:
            if not path.exists() or file_digest(path) != prior["sha256"]:
                raise ValueError("Restore prior checkpoint before proceeding")
            continue
        payload = load_checkpoint(path, job["lineage"])
        new = 0
        if payload is None:
            if path.exists():
                raise ValueError("Pending checkpoint lineage differs")
            with Progress().stage("terminal_" + "_".join(map(str, job["key"].values()))):
                payload = run_game(**job["key"])
                save_checkpoint(path, job["lineage"], payload)
            new = 1
        validate_episode(payload, job["key"])
        print(
            json.dumps(
                {
                    "path": job["path"],
                    "key": job["key"],
                    "new_games": new,
                    "sha256": file_digest(path),
                    "upload_required": True,
                }
            ),
            flush=True,
        )
        return
    print(json.dumps({"complete": True, "new_games": 0}), flush=True)


if __name__ == "__main__":
    main()
