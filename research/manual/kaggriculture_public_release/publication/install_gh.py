"""Optional user-run GitHub CLI installer. No tokens, account calls or ML installs.

Downloads the current stable official Linux binary plus release checksums.
Nothing is installed if gh already exists. No shell pipeline or sudo is used.
"""
from __future__ import annotations
import hashlib, io, json, os, platform, shutil, sys, tarfile, tempfile, time, urllib.request
from pathlib import Path
START=time.monotonic()
def fetch(url,limit):
    if not url.startswith(('https://api.github.com/repos/cli/cli/releases/', 'https://github.com/cli/cli/releases/download/')):
        raise ValueError('Unexpected download URL')
    req=urllib.request.Request(url,headers={'User-Agent':'kaggriculture-manual-setup'})
    with urllib.request.urlopen(req,timeout=20) as response:
        parts=[];total=0
        while True:
            if time.monotonic()-START>90:raise TimeoutError('90-second installer cap')
            block=response.read(min(1024**2,limit-total+1))
            if not block:break
            total+=len(block)
            if total>limit:raise ValueError('Download exceeds bound')
            parts.append(block)
    return b''.join(parts)
def main():
    if shutil.which('gh'):
        print('GitHub CLI already available; nothing installed');return
    arch={'x86_64':'amd64','aarch64':'arm64'}.get(platform.machine())
    if platform.system()!='Linux' or not arch:raise ValueError('Installer supports Linux amd64/arm64 only')
    r=json.loads(fetch('https://api.github.com/repos/cli/cli/releases/latest',2*1024**2))
    version=r['tag_name'].removeprefix('v'); name=f'gh_{version}_linux_{arch}.tar.gz'
    assets={x['name']:x['browser_download_url'] for x in r['assets']}
    sums=fetch(assets[f'gh_{version}_checksums.txt'],2*1024**2).decode()
    expected=next(line.split()[0] for line in sums.splitlines() if line.split()[-1].lstrip('*')==name)
    data=fetch(assets[name],100*1024**2)
    if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Binary archive checksum mismatch')
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as t:
        member=t.getmember(f'gh_{version}_linux_{arch}/bin/gh')
        if not member.isfile() or member.size>120*1024**2:raise ValueError('Unexpected binary archive member')
        payload=t.extractfile(member).read()
    target=Path.home()/'.local/bin/gh';target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():raise ValueError('Existing gh path is not on PATH; add ~/.local/bin rather than overwrite')
    with target.open('xb') as handle:handle.write(payload);handle.flush();os.fsync(handle.fileno())
    target.chmod(0o755)
    print('Installed',target,'version',version,'archive SHA256 verified')
if __name__=='__main__':main()
