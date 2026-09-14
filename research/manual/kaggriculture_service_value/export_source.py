"""User-run source-only export plan. Does not call Git or publish anything."""
import argparse,json,hashlib
from pathlib import Path
BASE=Path(__file__).resolve().parent
TARGET=Path.home()/'projects/kaggriculture-manual/research/manual/service_value'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');a=ap.parse_args()
    manifest=json.loads((BASE/'PACKAGE_MANIFEST.json').read_text());items=[]
    for name in sorted(set(manifest['files'])|set(manifest['notebooks'])|{'PACKAGE_MANIFEST.json'}):
        p=BASE/name
        if p.is_symlink() or not p.resolve().is_relative_to(BASE):raise ValueError('Unsafe source path')
        body=p.read_bytes()
        if name in manifest['files'] and hashlib.sha256(body).hexdigest()!=manifest['files'][name]:raise ValueError('Source hash differs: '+name)
        if name.endswith('.ipynb'):
            n=json.loads(body)
            for c in n['cells']:
                if c['cell_type']=='code':c['outputs']=[];c['execution_count']=None
            body=json.dumps(n,indent=1).encode()
        dest=TARGET/name
        if dest.exists() and dest.read_bytes()!=body:raise ValueError('Refusing to overwrite differing export: '+str(dest))
        items.append((dest,body));print(dest)
    if a.apply:
        for dest,body in items:
            dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():
                with dest.open('xb') as f:f.write(body)
        print('SOURCE_EXPORTED_NO_GIT_ACTIONS')
    else:print('PLAN_ONLY: review; --apply copies source without notebook outputs')
if __name__=='__main__':main()
