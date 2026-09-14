"""Small synthetic integrity tests: no imports of agents or simulator packages."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/verify_publication_snapshot.py"
SPEC = importlib.util.spec_from_file_location("publication_snapshot", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load publication verifier")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class PublicationSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = "research/manual/example/example.py"
        self.write(self.source, b"value = 1\n")
        self.notebook = {
            "nbformat": 4,
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["print(1)\n"],
                    "execution_count": None,
                    "outputs": [],
                }
            ],
        }
        self.write(VERIFIER.OVERVIEW, json.dumps(self.notebook).encode())
        manifest = {
            "files": [
                {"package": "example", "relative": "example.py", **self.metadata(self.source)}
            ]
        }
        self.write(VERIFIER.MANIFEST, json.dumps(manifest).encode())
        self.tracked = {self.source, VERIFIER.OVERVIEW, VERIFIER.MANIFEST}
        self.relock()

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def metadata(self, name):
        data = (self.root / name).read_bytes()
        return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    def relock(self):
        lock = {
            "schema_version": 1,
            "source_commit": "0" * 40,
            "files": [{"path": name, **self.metadata(name)} for name in sorted(self.tracked)],
        }
        self.write(VERIFIER.LOCK, json.dumps(lock).encode())

    def test_correct_snapshot(self):
        report = VERIFIER.verify(self.root, self.tracked)
        self.assertEqual(report["locked_files"], 3)
        self.assertFalse(report["research_executed"])

    def test_changed_source_is_rejected(self):
        self.write(self.source, b"value = 2\n")
        with self.assertRaisesRegex(ValueError, "Published bytes differ"):
            VERIFIER.verify(self.root, self.tracked)

    def test_unlisted_tracked_file_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Lock coverage differs"):
            VERIFIER.verify(self.root, self.tracked | {"research/manual/other.py"})

    def test_missing_tracked_file_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Lock coverage differs"):
            VERIFIER.verify(self.root, self.tracked - {self.source})

    def test_parent_escape_is_rejected(self):
        with self.assertRaises(ValueError):
            VERIFIER.safe_path(self.root, "research/manual/../../escape.py")

    def test_absolute_path_is_rejected(self):
        with self.assertRaises(ValueError):
            VERIFIER.safe_path(self.root, "/etc/passwd")

    def test_symlink_is_rejected(self):
        original = self.root / self.source
        original.unlink()
        original.symlink_to(self.root / VERIFIER.OVERVIEW)
        with self.assertRaisesRegex(ValueError, "Symlinked"):
            VERIFIER.verify(self.root, self.tracked)

    def test_bad_python_is_rejected_even_after_relocking(self):
        self.write(self.source, b"def broken(:\n")
        self.relock()
        with self.assertRaises(SyntaxError):
            VERIFIER.verify(self.root, self.tracked)

    def test_unexecuted_cells_are_reported_not_invented(self):
        report = VERIFIER.verify(self.root, self.tracked)
        self.assertEqual(report["unexecuted_cells"], 1)
        self.assertEqual(self.notebook["cells"][0]["execution_count"], None)

    def test_historical_error_outputs_are_not_hidden(self):
        self.notebook["cells"][0]["outputs"] = [
            {"output_type": "error", "ename": "ValueError", "evalue": "old evidence"}
        ]
        self.write(VERIFIER.OVERVIEW, json.dumps(self.notebook).encode())
        self.relock()
        self.assertEqual(VERIFIER.verify(self.root, self.tracked)["error_outputs"], 1)

    def test_invalid_notebook_is_rejected(self):
        self.write(VERIFIER.OVERVIEW, b'{"nbformat":4,"cells":null}')
        self.relock()
        with self.assertRaisesRegex(ValueError, "Invalid notebook"):
            VERIFIER.verify(self.root, self.tracked)

    def test_original_manifest_mismatch_is_rejected(self):
        manifest = json.loads((self.root / VERIFIER.MANIFEST).read_bytes())
        manifest["files"][0]["sha256"] = "0" * 64
        self.write(VERIFIER.MANIFEST, json.dumps(manifest).encode())
        self.relock()
        with self.assertRaisesRegex(ValueError, "manifest disagrees"):
            VERIFIER.verify(self.root, self.tracked)


if __name__ == "__main__":
    unittest.main()
