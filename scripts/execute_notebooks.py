"""Execute the canonical notebooks in fresh kernels, preserving their filenames."""

import argparse
import os
import sys
from pathlib import Path

import nbformat
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient

from kaggriculture_research.progress import Progress


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--foundation-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.environ["PYTHONPATH"] = str(root / "src")
    # Install only a project-local kernelspec, not a machine-wide notebook default.
    from ipykernel.kernelspec import install

    install(prefix=str(root / ".venv"), kernel_name="kaggriculture", user=False)
    manager = KernelSpecManager(kernel_dirs=[str(root / ".venv/share/jupyter/kernels")])
    spec = manager.get_kernel_spec("kaggriculture")
    if Path(spec.argv[0]).resolve() != Path(sys.executable).resolve():
        raise RuntimeError("Notebook kernel is not the active project environment")
    progress = Progress()
    for path in sorted((root / "notebooks").glob("*.ipynb")):
        if args.foundation_only and path.name not in (
            "00_environment.ipynb",
            "01_data_audit.ipynb",
        ):
            continue
        with progress.stage(path.name):
            notebook = nbformat.read(path, as_version=4)
            client = NotebookClient(
                notebook,
                timeout=120,
                kernel_name="kaggriculture",
                resources={"metadata": {"path": str(root)}},
            )
            from jupyter_client import KernelManager

            client.km = KernelManager(
                kernel_name="kaggriculture", kernel_spec_manager=manager, transport="ipc"
            )
            client.execute()
            nbformat.write(notebook, path)


if __name__ == "__main__":
    main()
