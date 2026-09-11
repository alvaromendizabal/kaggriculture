"""Install and verify the dedicated Kaggriculture Jupyter kernel.

This script is intentionally environment-only: it never runs project notebooks or
competition episodes. It binds the repository's ``src`` and ``scripts`` directories
inside the kernel interpreter, which remains reliable even when IPython rewrites
``sys.path`` during startup.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.metadata as metadata
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager

KERNEL_NAME = "kaggriculture"
DISPLAY_NAME = "Kaggriculture (Python 3.12)"
EXPECTED_ENGINE_SHA256 = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
EXPECTED_PACKAGES = {
    "kaggle-environments": "1.32.7",
    "ipykernel": "7.3.0",
    "jupyter-client": "8.10.0",
}


def utc_now() -> str:
    """Return an explicit UTC timestamp for durable reports."""
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path: Path) -> str:
    """Hash one file without loading project artifacts into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def kernel_bootstrap(repo: Path) -> str:
    """Build bootstrap code that survives IPython's startup path rewriting."""
    paths = [str(repo / "src"), str(repo / "scripts")]
    return (
        "import sys\n"
        "sys.dont_write_bytecode = True\n"
        f"project_paths = {paths!r}\n"
        "sys.path[:] = project_paths + [p for p in sys.path if p not in project_paths]\n"
        "from ipykernel.kernelapp import IPKernelApp\n"
        "app = IPKernelApp.instance()\n"
        "app.initialize()\n"
        "sys.path[:] = project_paths + [p for p in sys.path if p not in project_paths]\n"
        "app.start()\n"
    )


def kernel_document(repo: Path, interpreter: Path) -> dict[str, Any]:
    """Return a deterministic kernelspec with explicit project source binding."""
    return {
        "argv": [
            str(interpreter),
            "-I",
            "-B",
            "-c",
            kernel_bootstrap(repo),
            "-f",
            "{connection_file}",
        ],
        "display_name": DISPLAY_NAME,
        "language": "python",
        "env": {
            "MPLBACKEND": "Agg",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "LITELLM_LOCAL_MODEL_COST_MAP": "True",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        "metadata": {
            "kaggriculture": {
                "explicit_source_path": True,
                "repository_path": str(repo),
            }
        },
    }


def managed_kernel_dirs(home: Path, interpreter: Path) -> list[Path]:
    """Return the user and environment kernel locations that can shadow each other."""
    user = home / ".local/share/jupyter/kernels" / KERNEL_NAME
    environment = interpreter.parent.parent / "share/jupyter/kernels" / KERNEL_NAME
    return list(dict.fromkeys([user, environment]))


def verify_runtime(repo: Path, interpreter: Path) -> dict[str, Any]:
    """Verify the pinned interpreter and official Kaggriculture engine bytes."""
    if not interpreter.is_file() or not os.access(interpreter, os.X_OK):
        raise RuntimeError(f"Runtime interpreter is unavailable: {interpreter}")
    if sys.version_info[:2] != (3, 12) and Path(sys.executable).resolve() == interpreter.resolve():
        raise RuntimeError("Kernel installer must run with Python 3.12")

    versions = {name: metadata.version(name) for name in EXPECTED_PACKAGES}
    if versions != EXPECTED_PACKAGES:
        raise RuntimeError(f"Pinned package mismatch: {versions}")

    import kaggle_environments

    engine = (
        Path(kaggle_environments.__file__).resolve().parent
        / "envs/kaggriculture/kaggriculture.py"
    )
    engine_hash = sha256(engine)
    if engine_hash != EXPECTED_ENGINE_SHA256:
        raise RuntimeError(f"Official engine hash mismatch: {engine_hash}")
    return {
        "python": ".".join(map(str, sys.version_info[:3])),
        "packages": versions,
        "engine_file": str(engine),
        "engine_sha256": engine_hash,
    }


def write_kernel_specs(
    repo: Path, interpreter: Path, home: Path, backup_root: Path
) -> list[dict[str, Any]]:
    """Back up and replace only the dedicated Kaggriculture kernelspecs."""
    document = kernel_document(repo, interpreter)
    backup_root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for index, directory in enumerate(managed_kernel_dirs(home, interpreter)):
        if directory.is_symlink():
            raise RuntimeError(f"Kernel directory is a symlink: {directory}")
        target = directory / "kernel.json"
        previous_sha = None
        backup_path = None
        if target.exists():
            if target.is_symlink():
                raise RuntimeError(f"Kernel file is a symlink: {target}")
            previous_sha = sha256(target)
            backup_path = backup_root / f"kernel-{index}.json"
            shutil.copy2(target, backup_path)
        directory.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
        records.append(
            {
                "path": str(target),
                "sha256": sha256(target),
                "previous_sha256": previous_sha,
                "backup_path": str(backup_path) if backup_path else None,
            }
        )
    return records


def smoke_code(repo: Path, interpreter: Path) -> str:
    """Code executed inside a real kernel process for acceptance testing."""
    return f"""import io, json, os, pathlib, sys
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from kaggriculture_research.environment import engine_manifest
from kaggriculture_terminal.routing import terminal_features
root = pathlib.Path({str(repo)!r}).resolve()
manifest = engine_manifest()
if manifest['version'] != '1.32.7':
    raise RuntimeError('Simulator version mismatch inside kernel')
if pathlib.Path(sys.executable).resolve() != pathlib.Path({str(interpreter)!r}).resolve():
    raise RuntimeError('Unexpected Python interpreter inside kernel')
for module in (engine_manifest.__module__, terminal_features.__module__):
    loaded = sys.modules[module]
    pathlib.Path(loaded.__file__).resolve().relative_to(root / 'src')
figure = Figure(figsize=(2, 1))
FigureCanvasAgg(figure)
ax = figure.subplots()
ax.plot([0, 1], [0, 1])
image = io.BytesIO()
figure.savefig(image, format='png')
if not image.getvalue().startswith(b'\\x89PNG\\r\\n\\x1a\\n'):
    raise RuntimeError('Static figure smoke failed')
print('KAGGRICULTURE_KERNEL_RESULT ' + json.dumps({{
    'cwd': os.getcwd(), 'engine_version': manifest['version'],
    'executable': sys.executable, 'figure_bytes': image.tell(),
    'games_run': 0, 'project_notebooks_executed': 0
}}, sort_keys=True))
"""


def verify_kernel(repo: Path, interpreter: Path) -> dict[str, Any]:
    """Launch the normally discovered kernel from both canonical working directories."""
    expected = kernel_document(repo, interpreter)
    spec = KernelSpecManager().get_kernel_spec(KERNEL_NAME)
    if spec.argv != expected["argv"]:
        raise RuntimeError(f"Unexpected resolved kernel argv from {spec.resource_dir}")

    checks: list[dict[str, Any]] = []
    for directory in (repo, repo / "notebooks"):
        manager = KernelManager(kernel_name=KERNEL_NAME)
        client = None
        outputs: list[str] = []
        try:
            manager.start_kernel(cwd=str(directory))
            client = manager.client()
            client.start_channels()
            client.wait_for_ready(timeout=15)

            def capture(message: dict[str, Any]) -> None:
                if message.get("msg_type") == "stream":
                    outputs.append(message["content"].get("text", ""))
                elif message.get("msg_type") == "error":
                    outputs.append(json.dumps(message.get("content", {})))

            reply = client.execute_interactive(
                smoke_code(repo, interpreter),
                timeout=25,
                output_hook=capture,
                allow_stdin=False,
                store_history=False,
            )
            if reply["content"].get("status") != "ok":
                raise RuntimeError(f"Kernel execution failed: {reply['content']}")
            evidence = [
                json.loads(line.split(" ", 1)[1])
                for line in "".join(outputs).splitlines()
                if line.startswith("KAGGRICULTURE_KERNEL_RESULT ")
            ]
            if len(evidence) != 1:
                raise RuntimeError("Kernel did not emit exactly one acceptance record")
            checks.append(evidence[0])
        finally:
            if client is not None:
                client.stop_channels()
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
    return {
        "resource_dir": spec.resource_dir,
        "checks": checks,
        "all_passed": len(checks) == 2,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--report", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.monotonic()
    repo = args.repo.resolve()
    home = args.home.resolve()
    report_path = args.report or home / ".kaggriculture/notebook-kernel-report.json"
    interpreter = repo / ".venv/bin/python"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    backup_root = home / ".kaggriculture/kernel-backups" / dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"], cwd=repo, text=True
    )
    if status:
        raise RuntimeError("Refusing kernel setup in a dirty repository")

    runtime = verify_runtime(repo, interpreter)
    specs = write_kernel_specs(repo, interpreter, home, backup_root)
    kernel = verify_kernel(repo, interpreter)
    report = {
        "status": "PASSED",
        "started_utc": utc_now(),
        "finished_utc": utc_now(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "repository": str(repo),
        "head": head,
        "git_status": status,
        "runtime": runtime,
        "kernelspecs": specs,
        "kernel": kernel,
        "games_run": 0,
        "project_notebooks_executed": 0,
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
