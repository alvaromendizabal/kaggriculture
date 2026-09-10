"""Run the registered, resumable development feature experiment."""

import json
import os
from pathlib import Path

import boto3
from botocore.config import Config

from kaggriculture_research.experiment import run_experiment
from kaggriculture_research.progress import Progress


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/feature_research.json").read_text())
    foundation = json.loads((root / "configs/research.json").read_text())
    checkpoint_ready = None
    if run_id := os.environ.get("KAGGRICULTURE_SETUP_RUN"):
        aws = json.loads((root / "configs/aws.json").read_text())
        client = boto3.client(
            "s3",
            region_name=aws["region"],
            config=Config(
                retries={"mode": "standard", "total_max_attempts": 5},
                connect_timeout=10,
                read_timeout=60,
            ),
        )

        def checkpoint_ready(path):
            client.upload_file(
                str(path), aws["bucket"], f"runs/{run_id}/{path.relative_to(root).as_posix()}"
            )

    progress = Progress()
    with progress.stage("crop_feature_research"):
        result = run_experiment(root, protocol, foundation, progress, checkpoint_ready)
    print(json.dumps({k: result[k] for k in ("games", "reused_games", "feature_completion_gate")}))


if __name__ == "__main__":
    main()
