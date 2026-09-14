"""Atomic, bounded local artifacts; never executes cloud or Git writes."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import gzip, hashlib, json, os, tempfile

def utc(): return datetime.now(timezone.utc).isoformat()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(x): return hashlib.sha256(canonical(x)).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''): h.update(block)
    return h.hexdigest()
def inside(root,name):
    p=(Path(root)/name).resolve()
    if not p.is_relative_to(Path(root).resolve()): raise ValueError('Escaping path')
    return p
def atomic(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.partial-',dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
def write(p,x):atomic(p,json.dumps(x,indent=2,sort_keys=True,allow_nan=False).encode()+b'\n')
def save(p,fp,payload):
    p=Path(p)
    if p.exists(): raise ValueError('Refusing checkpoint overwrite')
    d={'fingerprint':fp,'payload':payload};d['checksum']=digest(d)
    atomic(p,gzip.compress(canonical(d),mtime=0))
    if load(p,fp)!=payload: raise ValueError('Checkpoint readback mismatch')
def load(p,fp):
    p=Path(p)
    if not p.exists():return None
    d=json.loads(gzip.decompress(p.read_bytes()));h=d.pop('checksum')
    if digest(d)!=h or d['fingerprint']!=fp:raise ValueError('Checkpoint identity/integrity mismatch')
    return d['payload']
def code_hash(root):
    return digest({str(p.relative_to(root)):sha(p) for p in sorted(Path(root).rglob('*.py')) if not {'outputs','__pycache__'}&set(p.parts)})
