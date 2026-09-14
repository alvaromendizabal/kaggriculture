"""Local atomic artifacts and strict checksums; no network or cloud operations."""
from pathlib import Path
from datetime import datetime, timezone
import gzip, hashlib, json, os, tempfile

def utc():
    return datetime.now(timezone.utc).isoformat()

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def digest(x):
    return hashlib.sha256(canonical(x)).hexdigest()

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def read(p):
    return json.loads(Path(p).read_text())

def inside(root, relative):
    p = (Path(root) / relative).resolve()
    if not p.is_relative_to(Path(root).resolve()):
        raise ValueError('Escaping artifact path')
    return p

def atomic(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.partial-', dir=p.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def write(p, x):
    atomic(p, json.dumps(x, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n')

def code_hash(root):
    root = Path(root)
    return digest({str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*.py')) if 'outputs' not in p.parts})

def save_cache(p, fp, payload):
    p = Path(p)
    if p.exists():
        raise ValueError('Refuse to overwrite completed checkpoint')
    doc = {'fingerprint': fp, 'payload': payload}
    doc['checksum'] = digest(doc)
    atomic(p, gzip.compress(canonical(doc), mtime=0))
    if load_cache(p, fp) != payload:
        raise ValueError('Checkpoint readback mismatch')

def load_cache(p, fp):
    p = Path(p)
    if not p.exists():
        return None
    doc = json.loads(gzip.decompress(p.read_bytes()))
    checksum = doc.pop('checksum')
    if checksum != digest(doc) or doc['fingerprint'] != fp:
        raise ValueError('Checkpoint integrity/lineage mismatch; preserve it')
    return doc['payload']
