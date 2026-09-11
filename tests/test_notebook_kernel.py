"""Kernel regressions. Synthetic packages test transport, not game correctness."""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jupyter_client.kernelspec import KernelSpecManager

SOURCE = Path(__file__).resolve().parents[1] / "scripts/setup_notebook_kernel.py"
SPEC = importlib.util.spec_from_file_location("setup_notebook_kernel", SOURCE)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class KernelTests(unittest.TestCase):
    def test_explicit_source_binding(self):
        doc = MOD.kernel_document(Path("/project"), Path("/runtime/python"))
        self.assertIn("-I", doc["argv"])
        self.assertIn("/project/src", doc["argv"][4])
        self.assertIn("/project/scripts", doc["argv"][4])
        self.assertEqual(doc["argv"][4].count("sys.path[:]"), 2)
        self.assertEqual(doc["argv"][-1], "{connection_file}")

    def test_source_paths_are_quoted(self):
        repo = Path("/tmp/project's folder")
        doc = MOD.kernel_document(repo, Path(sys.executable))
        compile(doc["argv"][4], "kernel_bootstrap", "exec")

    def test_atomic_report_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "report.json"
            MOD.atomic_json(dest, {"status": "ready"})
            self.assertEqual(json.loads(dest.read_text()), {"status": "ready"})
            self.assertFalse(dest.with_suffix(".json.tmp").exists())

    def test_changed_commit_stops_before_kernel_writes(self):
        before = {"commit": "changed", "status": ""}
        with patch.object(MOD, "snapshot", return_value=before):
            with self.assertRaisesRegex(RuntimeError, "commit changed"):
                MOD.configure(Path("/project"), Path("/unwritten/report.json"), "reviewed")

    def test_dirty_tree_stops_before_kernel_writes(self):
        with patch.object(MOD, "snapshot", return_value={"commit": "same", "status": " M x"}):
            with self.assertRaisesRegex(RuntimeError, "Local source edits"):
                MOD.configure(Path("/project"), Path("/unwritten/report.json"), "same")

    def test_genuine_kernels_from_two_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "project"
            (repo / "notebooks").mkdir(parents=True)
            for name in ("kaggriculture_research", "kaggriculture_livestock", "kaggriculture_terminal"):
                package = repo / "src" / name
                package.mkdir(parents=True)
                (package / "__init__.py").write_text("")
            manifest = {"version": "1.32.7", "files": {
                "envs/kaggriculture/kaggriculture.py": MOD.ENGINE_SHA256}}
            (repo / "src/kaggriculture_research/environment.py").write_text(
                "def engine_manifest():\n    return " + repr(manifest) + "\n")
            data = root / "jupyter"
            doc = MOD.kernel_document(repo, Path(os.path.abspath(sys.executable)))
            MOD.atomic_json(data / "kernels/kaggriculture/kernel.json", doc)
            with patch.dict(os.environ, {"JUPYTER_PATH": str(data)}):
                spec = KernelSpecManager().get_kernel_spec("kaggriculture")
                self.assertEqual(spec.argv, doc["argv"])
                results = MOD.smoke(repo, Path(os.path.abspath(sys.executable)))
            self.assertEqual(len(results), 2)
            self.assertEqual({x["cwd"] for x in results}, {str(repo), str(repo / "notebooks")})
            self.assertTrue(all(x["figure_bytes"] > 100 for x in results))
            self.assertTrue(all(x["games_run"] == 0 for x in results))


if __name__ == "__main__":
    unittest.main(verbosity=2)
