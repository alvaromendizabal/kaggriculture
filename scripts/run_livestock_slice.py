"""Operational recovery adapter: at most one new registered game per invocation.

This preserves the frozen game code, source registration and job identities.
It shortens execution sessions after transport disconnections; it changes no
policy, feature, seed, opponent, statistic or research budget.
"""

import argparse
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from run_livestock_research import register, upload_callback

from kaggriculture_livestock.experiment import job_plan, run_game, validate_episode
from kaggriculture_research.artifacts import (
    file_digest,
    load_checkpoint,
    save_checkpoint,
    write_json,
)
from kaggriculture_research.progress import Progress


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uploads", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/livestock_research.json").read_text())
    register(root, protocol)
    _, jobs = job_plan(root, protocol)
    manifest = json.loads(args.uploads.read_text())
    bucket = json.loads((root / "configs/aws.json").read_text())["bucket"]
    prefix = "runs/livestock-resource-loops-20260910/"
    if manifest["bucket"] != bucket or manifest["prefix"] != prefix:
        raise ValueError("Destination differs from the verified project bucket")
    for relative, url in manifest["uploads"].items():
        parsed = urlsplit(url)
        hosts = {f"{bucket}.s3.us-west-2.amazonaws.com", f"{bucket}.s3.amazonaws.com"}
        if (
            parsed.scheme != "https"
            or parsed.hostname not in hosts
            or unquote(parsed.path) != "/" + prefix + relative
        ):
            raise ValueError("Signed destination does not match the exact registered object")
    receipt = json.loads((root / "reports/livestock_uploads.json").read_text())
    ready, completed, new = upload_callback(root, args.uploads), 0, 0
    progress = Progress()
    for job in jobs:
        path = root / job["path"]
        prior = receipt["artifacts"].get(job["path"])
        if prior is not None:
            if not path.exists() or file_digest(path) != prior["sha256"]:
                raise ValueError(
                    "Completed local game missing or changed; restore before execution"
                )
            completed += 1
            continue
        payload = load_checkpoint(path, job["lineage"])
        if payload is None:
            if path.exists():
                raise ValueError("Existing game lineage differs; do not overwrite")
            with progress.stage("livestock_" + "_".join(map(str, job["key"].values()))):
                payload = run_game(**job["key"])
                save_checkpoint(path, job["lineage"], payload)
            new = 1
        validate_episode(payload, job["key"])
        ready(path)
        completed += 1
        break
    status = {
        "completed_games": completed,
        "complete": completed == 64,
        "new_games": new,
        "adapter_sha256": file_digest(Path(__file__)),
        "scope": "one-game operational slices within the registered eight-game maximum",
    }
    write_json(root / "reports/livestock_slice_progress.json", status)
    print(json.dumps(status), flush=True)


if __name__ == "__main__":
    main()
