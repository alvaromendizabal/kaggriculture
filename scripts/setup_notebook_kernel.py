"""Configure and verify the project kernel without executing research notebooks.

Run with the existing project Python. No dependency installation or Git mutation.
The acceptance test starts real Jupyter kernels from two working directories.
"""

import argparse
import hashlib
import io
import json
import os
import signal
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


NAME = "kaggriculture"
ENGINE_SHA256 = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit(event: str, **fields: Any) -> None:
    print(json.dumps({"utc": datetime.now(UTC).isoformat(), "event": event, **fields}), flush=True)


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    with temporary.open("w") as out:
        json.dump(value, out, indent=2)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())
    temporary.replace(path)


def kernel_document(repo: Path, python: Path) -> dict:
    """Bind source inside Python; -I intentionally ignores inherited PYTHONPATH."""
    paths = [str(repo / "src"), str(repo / "scripts")]
    bootstrap = (
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
    return {
        "argv": [str(python), "-I", "-B", "-c", bootstrap, "-f", "{connection_file}"],
        "display_name": "Kaggriculture (Python 3.12)",
        "language": "python",
        "env": {
            "MPLBACKEND": "Agg",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "LITELLM_LOCAL_MODEL_COST_MAP": "True",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
        },
        "metadata": {"kaggriculture": {"source_binding": "explicit", "repository": str(repo)}},
    }


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(repo), *args],
        text=True, timeout=15,
    ).strip()


def snapshot(repo: Path) -> dict:
    notebooks = {}
    for path in sorted((repo / "notebooks").glob("*.ipynb")):
        nb = json.loads(path.read_text())
        code = [c for c in nb["cells"] if c["cell_type"] == "code" and "".join(c["source"]).strip()]
        notebooks[path.name] = {
            "sha256": digest(path), "code_cells": len(code),
            "unexecuted": sum(c.get("execution_count") is None for c in code),
            "errors": sum(o.get("output_type") == "error" for c in code for o in c.get("outputs", [])),
        }
    return {"commit": git(repo, "rev-parse", "HEAD"), "branch": git(repo, "branch", "--show-current"),
            "status": git(repo, "status", "--porcelain", "--untracked-files=all"), "notebooks": notebooks}


def smoke(repo: Path, python: Path) -> list[dict]:
    from jupyter_client import KernelManager

    # Network remains available to the server; only this disposable smoke cell
    # disallows external socket connections, while preserving loopback transport.
    cell = f'''
import hashlib, importlib, io, json, os, pathlib, socket, sys
old_connect = socket.socket.connect
def local_only(self, address):
    if isinstance(address, tuple) and address[0] not in ("127.0.0.1", "::1", "localhost"):
        raise RuntimeError("External network disabled in acceptance cell")
    return old_connect(self, address)
socket.socket.connect = local_only
try:
    root = pathlib.Path({str(repo)!r})
    origins = {{}}
    for name in ("kaggriculture_research", "kaggriculture_livestock", "kaggriculture_terminal"):
        module = importlib.import_module(name)
        where = pathlib.Path(module.__file__).resolve()
        where.relative_to((root / "src").resolve())
        origins[name] = str(where)
    from kaggriculture_research.environment import engine_manifest
    manifest = engine_manifest()
    if manifest["version"] != "1.32.7":
        raise RuntimeError("Unexpected engine version")
    if manifest["files"]["envs/kaggriculture/kaggriculture.py"] != {ENGINE_SHA256!r}:
        raise RuntimeError("Unexpected simulator bytes")
    if os.path.abspath(sys.executable) != {str(python)!r}:
        raise RuntimeError("Unexpected kernel interpreter")
    import numpy, pandas, nbformat, nbclient, plotly
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    fig = Figure(figsize=(2, 1))
    FigureCanvasAgg(fig)
    fig.add_subplot().plot([0, 1], [0, 1])
    out = io.BytesIO()
    fig.savefig(out, format="png")
    if not out.getvalue().startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
        raise RuntimeError("PNG rendering failed")
    print("KERNEL_RESULT " + json.dumps({{"cwd": os.getcwd(), "python": sys.version.split()[0],
        "executable": sys.executable, "origins": origins, "engine_version": manifest["version"],
        "figure_bytes": out.tell(), "games_run": 0}}))
finally:
    socket.socket.connect = old_connect
'''
    results = []
    for directory in (repo, repo / "notebooks"):
        emit("kernel_start", cwd=str(directory))
        manager = KernelManager(kernel_name=NAME)
        client = None
        output = []
        try:
            manager.start_kernel(cwd=str(directory))
            client = manager.client()
            client.start_channels()
            client.wait_for_ready(timeout=20)
            def capture(message: dict) -> None:
                if message.get("msg_type") == "stream":
                    output.append(message["content"].get("text", ""))
            reply = client.execute_interactive(cell, timeout=35, allow_stdin=False,
                                               store_history=False, output_hook=capture)
            if reply["content"].get("status") != "ok":
                raise RuntimeError(json.dumps(reply["content"]))
            evidence = [json.loads(line.split(" ", 1)[1]) for line in "".join(output).splitlines()
                        if line.startswith("KERNEL_RESULT ")]
            if len(evidence) != 1:
                raise RuntimeError("Missing kernel evidence")
            results.extend(evidence)
            emit("kernel_passed", **evidence[0])
        finally:
            if client is not None:
                client.stop_channels()
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
    return results


def configure(repo: Path, report_path: Path, expected_commit: str | None = None) -> dict:
    from jupyter_client.kernelspec import KernelSpecManager, NoSuchKernel

    python = Path(os.path.abspath(sys.executable))
    before = snapshot(repo)
    if expected_commit is not None and before["commit"] != expected_commit:
        raise RuntimeError("Workspace commit changed; no kernel configuration modified")
    if before["status"]:
        raise RuntimeError("Local source edits exist; no source or kernel settings overwritten")
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Run using the already-installed project Python 3.12")
    spec = kernel_document(repo, python)
    target = Path.home() / ".local/share/jupyter/kernels" / NAME
    destinations = [target]
    try:
        existing = Path(KernelSpecManager().get_kernel_spec(NAME).resource_dir)
        if existing not in destinations:
            existing.relative_to(Path.home())
            destinations.append(existing)
    except NoSuchKernel:
        pass
    backup_root = report_path.parent / ("kernel-backup-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    originals = {}
    backups = []
    for i, directory in enumerate(destinations):
        path = directory / "kernel.json"
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise RuntimeError("Symlink kernel configuration; preserved")
        raw = path.read_bytes() if path.exists() else None
        originals[path] = raw
        if raw is not None:
            old = json.loads(raw)
            if old.get("language") != "python" or "Kaggriculture" not in old.get("display_name", ""):
                raise RuntimeError("Unrecognized same-name kernel; preserved")
            backup = backup_root / str(i) / "kernel.json"
            backup.parent.mkdir(parents=True)
            backup.write_bytes(raw)
            backups.append({"target": str(path), "backup": str(backup), "sha256": digest(backup)})
    result = {"status": "RUNNING", "before": before, "kernel_backups": backups,
              "games_run": 0, "project_notebooks_executed": 0, "package_installations": 0}
    atomic_json(report_path, result)
    try:
        for path in originals:
            atomic_json(path, spec)
        selected = KernelSpecManager().get_kernel_spec(NAME)
        if selected.argv != spec["argv"]:
            raise RuntimeError("Jupyter selected a different kernel")
        result["kernel_spec"] = str(Path(selected.resource_dir) / "kernel.json")
        result["checks"] = smoke(repo, python)
        result["after"] = snapshot(repo)
        if result["after"] != before:
            raise RuntimeError("Source or notebook bytes changed during acceptance")
        result["status"] = "NOTEBOOK_WORKSPACE_READY"
    except BaseException as exc:
        for path, raw in originals.items():
            if raw is None:
                path.unlink(missing_ok=True)
            else:
                atomic_json(path, json.loads(raw))
        result.update(status="FAILED", error=f"{type(exc).__name__}: {exc}", kernel_rollback=True)
        raise
    finally:
        result["finished_utc"] = datetime.now(UTC).isoformat()
        atomic_json(report_path, result)
        emit("kernel_result", **result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--expected-commit")
    args = parser.parse_args()
    def expired(signum: int, frame: Any) -> None:
        raise TimeoutError("Kernel acceptance exceeded 120 seconds")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(120)
    try:
        configure(args.repo.resolve(), args.report, args.expected_commit)
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
