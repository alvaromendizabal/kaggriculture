"""Create or restore a byte-verified archive of the completed per-game audit cache."""

import argparse
import hashlib
import io
import json
import tempfile
import zipfile
from pathlib import Path

from kaggriculture_research.artifacts import file_digest, load_checkpoint, write_atomic


def verify_entry(path: Path, item: dict) -> None:
    if file_digest(path) != item["sha256"]:
        raise ValueError("Audit archive entry checksum differs")
    result = load_checkpoint(path, item["lineage"])
    if result is None or result["mismatches"] != 0:
        raise ValueError("Audit entry lineage or result differs")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("create", "restore", "check"))
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    report = json.loads((root / "reports/livestock_integrity.json").read_text())
    if not report["complete"] or len(report["artifacts"]) != 64:
        raise ValueError("Final archive requires all 64 completed audits")
    items = {a["path"]: a for a in report["artifacts"]}
    if len(items) != 64:
        raise ValueError("Duplicate audit archive names")
    for relative in items:
        if not relative.startswith("artifacts/livestock_audits/") or ".." in Path(relative).parts:
            raise ValueError("Unsafe audit archive entry")
    archive = args.archive or root / "artifacts/livestock_audits.zip"
    if args.mode == "create":
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for relative, item in sorted(items.items()):
                verify_entry(root / relative, item)
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(info, (root / relative).read_bytes())
        write_atomic(archive, buffer.getvalue())
    restored = 0
    with zipfile.ZipFile(archive) as bundle, tempfile.TemporaryDirectory() as temporary:
        if len(bundle.namelist()) != 64 or set(bundle.namelist()) != set(items):
            raise ValueError("Archive contents differ from the exact audit manifest")
        for relative, item in sorted(items.items()):
            data = bundle.read(relative)
            candidate = Path(temporary) / "candidate.json.gz"
            write_atomic(candidate, data)
            verify_entry(candidate, item)
            if args.mode == "restore":
                target = root / relative
                if target.exists():
                    verify_entry(target, item)
                else:
                    write_atomic(target, data)
                    restored += 1
    print(
        json.dumps(
            {
                "verified_audits": 64,
                "restored_audits": restored,
                "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "games_executed": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
