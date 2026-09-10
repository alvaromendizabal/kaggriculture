"""Recover progress from completed checkpoints without running games or uploading."""

import json
from pathlib import Path

from kaggriculture_research.artifacts import file_digest, load_checkpoint, write_json
from kaggriculture_research.supply_experiment import job_plan, validate_episode


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/supply_research.json").read_text())
    common, jobs = job_plan(root, protocol)
    receipt_path = root / "reports/supply_uploads.json"
    receipts = json.loads(receipt_path.read_text())["artifacts"] if receipt_path.exists() else {}
    completed = []
    for job in jobs:
        path = root / job["path"]
        if not path.exists():
            continue
        payload = load_checkpoint(path, job["lineage"])
        if payload is None:
            raise ValueError("Existing episode has inconsistent lineage")
        validate_episode(payload, job["key"])
        sha = file_digest(path)
        receipt = receipts.get(job["path"])
        if receipt and receipt["sha256"] != sha:
            raise ValueError("Recorded upload differs from completed local episode")
        completed.append(
            {
                **job["key"],
                "path": job["path"],
                "sha256": sha,
                "semantic_sha256": payload["semantic_sha256"],
                "upload_receipt_present": receipt is not None,
            }
        )
    report = {
        "experiment": protocol["experiment"],
        "lineage": common,
        "status": "episodes_complete" if len(completed) == len(jobs) else "episodes_incomplete",
        "completed_games": len(completed),
        "expected_games": len(jobs),
        "completed_with_upload_receipt": sum(a["upload_receipt_present"] for a in completed),
        "artifact_manifest": completed,
        "feature_completion_gate": "closed",
        "new_games_run_by_inspection": 0,
    }
    write_json(root / "reports/supply_progress.json", report)
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "status",
                    "completed_games",
                    "expected_games",
                    "completed_with_upload_receipt",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
