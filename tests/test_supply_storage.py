"""Storage receipts must verify bytes, version, and encryption, not just existence."""

import hashlib
import io
import runpy
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("invalid", [None, "content", "bytes", "version", "etag", "encryption"])
def test_s3_verification_rejects_any_receipt_mismatch(monkeypatch, invalid):
    verify = runpy.run_path(str(ROOT / "scripts/verify_supply_storage.py"))["verify_download"]
    content = b"registered-evidence"
    receipt = {
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
        "version_id": "version-1",
        "etag": "etag-1",
    }
    response = io.BytesIO(b"different-content" if invalid == "content" else content)
    response.headers = {
        "x-amz-version-id": "version-2" if invalid == "version" else "version-1",
        "x-amz-server-side-encryption": "none" if invalid == "encryption" else "AES256",
        "ETag": '"different"' if invalid == "etag" else '"etag-1"',
    }
    if invalid == "bytes":
        receipt["bytes"] += 1
    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: response)
    item = {"url": "https://authorized.invalid/artifact", "path": "artifact", "key": "run/artifact"}
    if invalid is not None:
        with pytest.raises(ValueError, match="differ from upload receipt"):
            verify(item, receipt)
    else:
        result = verify(item, receipt)
        assert result["remote_bytes_sha256_verified"] and result["remote_receipt_matched"]
        assert result["sha256"] == receipt["sha256"]
