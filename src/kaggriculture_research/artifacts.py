"""Atomic, content-verified checkpoints. File existence alone is never a cache hit."""

import gzip
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".checkpoint-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path: Path, value: Any) -> None:
    write_atomic(
        path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    )


def save_checkpoint(path: Path, lineage: dict[str, Any], payload: Any) -> None:
    envelope = {"schema_version": 1, "lineage": lineage, "payload": payload}
    envelope["checksum"] = digest(envelope)
    write_atomic(path, gzip.compress(canonical(envelope), mtime=0))


def load_checkpoint(path: Path, lineage: dict[str, Any]) -> Any | None:
    if not path.exists():
        return None
    envelope = json.loads(gzip.decompress(path.read_bytes()))
    checksum = envelope.pop("checksum")
    if checksum != digest(envelope):
        raise ValueError(f"Checkpoint checksum mismatch: {path}")
    if envelope["schema_version"] != 1:
        raise ValueError(f"Unsupported checkpoint schema: {path}")
    if envelope["lineage"] != lineage:
        return None
    return envelope["payload"]
