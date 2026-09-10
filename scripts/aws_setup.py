"""Verify this release in the dedicated SageMaker space and persist its evidence."""

import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import boto3
from botocore.config import Config


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "configs/aws.json").read_text())
    run_id = os.environ["KAGGRICULTURE_SETUP_RUN"]
    source_sha = os.environ["KAGGRICULTURE_SOURCE_SHA256"]
    prefix = f"runs/{run_id}"
    client = boto3.client(
        "s3",
        region_name=config["region"],
        config=Config(
            retries={"mode": "standard", "total_max_attempts": 5},
            connect_timeout=10,
            read_timeout=60,
        ),
    )
    log_path = root / "logs" / f"{run_id}.log"
    log_path.parent.mkdir(exist_ok=True)
    start = time.monotonic()
    deadline = start + config["setup_max_seconds"]
    steps = []

    def status(state: str, **extra) -> None:
        payload = {
            "status": state,
            "run_id": run_id,
            "source_sha256": source_sha,
            "utc": datetime.now(UTC).isoformat(),
            "steps": steps,
            "elapsed_seconds": round(time.monotonic() - start, 2),
            **extra,
        }
        client.put_object(
            Bucket=config["bucket"],
            Key=f"{prefix}/status.json",
            Body=json.dumps(payload).encode(),
            ContentType="application/json",
        )

    def upload_log() -> None:
        client.upload_file(str(log_path), config["bucket"], f"{prefix}/setup.log")

    status("running")
    stop = threading.Event()
    with log_path.open("a", buffering=1) as log:

        def heartbeat() -> None:
            while not stop.wait(15):
                log.write(
                    json.dumps(
                        {
                            "utc": datetime.now(UTC).isoformat(),
                            "event": "heartbeat",
                            "stage": steps[-1]["name"] if steps else "setup",
                            "total_elapsed_seconds": round(time.monotonic() - start, 2),
                        }
                    )
                    + "\n"
                )
                log.flush()
                upload_log()

        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        commands = [
            ("install_uv", [sys.executable, "-m", "pip", "install", "--user", "uv==0.12.8"]),
            ("environment", [sys.executable, "-m", "uv", "sync", "--frozen"]),
            ("tests", [str(root / ".venv/bin/python"), "-m", "pytest", "-q"]),
            ("foundation", [str(root / ".venv/bin/python"), "scripts/run_foundation.py"]),
            (
                "feature_research",
                [str(root / ".venv/bin/python"), "scripts/run_feature_research.py"],
            ),
            ("notebooks", [str(root / ".venv/bin/python"), "scripts/execute_notebooks.py"]),
        ]
        if os.environ.get("KAGGRICULTURE_RESEARCH_STAGE") == "relationships":
            # Preserve the first study and its 80 valid checkpoints; do not rerun it.
            commands = commands[:3] + [
                (
                    "relationship_research",
                    [str(root / ".venv/bin/python"), "scripts/run_relationship_research.py"],
                ),
                (
                    "notebook_build",
                    [str(root / ".venv/bin/python"), "scripts/build_research_notebook.py"],
                ),
                ("notebooks", [str(root / ".venv/bin/python"), "scripts/execute_notebooks.py"]),
            ]
        env = {**os.environ, "PYTHONPATH": str(root / "src"), "MPLBACKEND": "Agg"}
        try:
            for name, cmd in commands:
                stage_start = time.monotonic()
                steps.append({"name": name, "status": "running"})
                status("running")
                with subprocess.Popen(
                    cmd,
                    cwd=root,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                ) as process:
                    try:
                        code = process.wait(timeout=max(1, deadline - time.monotonic()))
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                        raise
                steps[-1].update(
                    status="passed" if code == 0 else "failed",
                    elapsed_seconds=round(time.monotonic() - stage_start, 2),
                )
                log.flush()
                upload_log()
                if code:
                    raise RuntimeError(f"{name} exited with code {code}")
            manifest = []
            import hashlib

            for folder in ("artifacts", "notebooks", "reports"):
                for path in sorted((root / folder).rglob("*")):
                    if path.is_file():
                        relative = path.relative_to(root).as_posix()
                        client.upload_file(str(path), config["bucket"], f"{prefix}/{relative}")
                        manifest.append(
                            {
                                "path": relative,
                                "bytes": path.stat().st_size,
                                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            }
                        )
            status("completed", artifacts=manifest)
        except BaseException as exc:
            status("failed", error=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            stop.set()
            thread.join()
            log.flush()
            upload_log()


if __name__ == "__main__":
    main()
