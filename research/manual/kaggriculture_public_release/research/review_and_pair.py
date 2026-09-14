"""Manual two-round outcome stage. No Git writes, cloud API calls, or installs.

Uses the exact user-screened implementation rather than rewriting its actor.
Only paired block b1 is exposed here. No loop over later blocks is provided.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,io,json,os,queue,signal,subprocess,sys,tempfile,threading,time
from datetime import datetime,timezone
from pathlib import Path
from relative_features import augment,COLLECTION_FIELDS,MAINTENANCE_FIELDS
BASE=Path(__file__).resolve().parent
OUT=BASE/'outputs'
MAP={'21':'19','22':'20'}

def utc():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def write(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    fd,t=tempfile.mkstemp(prefix='.partial-',dir=p.parent)
    try:
        with os.fdopen(fd,'w') as f:json.dump(x,f,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
        os.replace(t,p)
    finally:
        if os.path.exists(t):os.unlink(t)

def inputs(home: Path):
    old=home/'kaggriculture_service_value';expected=read(BASE/'EXPECTED_INPUTS.json')
    for rel,h in expected['paths'].items():
        p=old/rel
        if not p.is_file() or p.is_symlink() or sha(p)!=h:
            raise ValueError('Reviewed screen or protocol changed: '+rel)
    tree={str(p.relative_to(old)):sha(p) for p in sorted(old.rglob('*.py'))
          if not {'outputs','__pycache__'} & set(p.parts)}
    if hashlib.sha256(canonical(tree)).hexdigest()!=expected['source_code_sha256']:
        raise ValueError('User-screened implementation changed; do not overwrite or reset')
    runtime=read(home/'kaggriculture_manual_resume/state/runtime.json')
    if Path(sys.executable).absolute()!=Path(runtime['executable']).absolute():
        raise ValueError('Use Kaggriculture Manual (verified source)')
    for r in ('19','20'):
        report=read(old/f'outputs/round{r}/screen/report.json')
        tests=report['tests']
        if report['status']!='FEATURE_SCREEN_COMPLETE' or report['decision']!='REVIEW_REQUIRED_BEFORE_GAMES':
            raise ValueError('Activated reviewed screen required')
        if any(tests[k] for k in ('failures','errors','skipped')):
            raise ValueError('Previous tests did not pass')
    return old,expected

def stream(command: list[str],cwd: Path,logfile: Path,cap: float):
    """Bound the existing supervisor; it owns/terminates its detached worker."""
    logfile.parent.mkdir(parents=True,exist_ok=True)
    child=subprocess.Popen(command,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                           text=True,bufsize=1,start_new_session=True)
    q=queue.Queue()
    def drain():
        for line in child.stdout:q.put(line)
        q.put(None)
    threading.Thread(target=drain,daemon=True).start();start=time.monotonic();done=False
    def stop():
        if child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
    try:
        with logfile.open('a') as log:
            while not done or child.poll() is None:
                if time.monotonic()-start>cap:raise TimeoutError('Outer stage deadline; preserve diagnostic files')
                try:line=q.get(timeout=.2)
                except queue.Empty:continue
                if line is None:done=True;continue
                print(line,end='',flush=True);log.write(line);log.flush()
            if child.wait()!=0:raise RuntimeError('Stage failed. Bundle diagnostics; no unchanged retry')
    except BaseException:stop();raise

def csv_rows(path):
    raw=Path(path).read_bytes()
    if str(path).endswith('.gz'):raw=gzip.decompress(raw)
    return list(csv.DictReader(io.StringIO(raw.decode())))

def analyze(rid,home):
    old,_=inputs(home);family=MAP[rid]
    rows=csv_rows(old/f'outputs/round{family}/screen/task_features.csv.gz')
    data=augment(rows,family);folder=OUT/f'round{rid}';folder.mkdir(parents=True,exist_ok=True)
    raw=io.StringIO();w=csv.DictWriter(raw,fieldnames=list(data[0]) if data else []);w.writeheader();w.writerows(data)
    dest=folder/'relative_task_features.csv.gz';compressed=gzip.compress(raw.getvalue().encode(),mtime=0)
    if dest.exists() and dest.read_bytes()!=compressed:raise ValueError('Existing derived features differ')
    if not dest.exists():
        fd,temp=tempfile.mkstemp(prefix='.feature-',dir=folder)
        try:
            with os.fdopen(fd,'wb') as f:f.write(compressed);f.flush();os.fsync(f.fileno())
            os.replace(temp,dest)
        finally:
            if os.path.exists(temp):os.unlink(temp)
    if hashlib.sha256(dest.read_bytes()).digest()!=hashlib.sha256(compressed).digest():
        raise ValueError('Derived feature readback mismatch')
    names=COLLECTION_FIELDS if family=='19' else MAINTENANCE_FIELDS
    registry=[{'feature':n,'distinct_values':len({r[n] for r in data}),
               'nonzero_fraction':sum(r[n]!=0 for r in data)/max(1,len(data)),
               'status':'diagnostic_only_not_used_in_actor'} for n in names]
    write(folder/'feature_analysis.json',{'status':'RELATIVE_FEATURE_ANALYSIS_COMPLETE','round':rid,
        'policy_family':family,'rows':len(rows),'new_descriptors':12,'original_task_descriptors':32,
        'original_state_summaries':12,'total_task_descriptors':44,'registry':registry,
        'source_table_sha256':sha(old/f'outputs/round{family}/screen/task_features.csv.gz'),
        'output_sha256':sha(dest),'new_games':0,'prospective_performance_claim':False})
    print('RELATIVE_FEATURE_ANALYSIS_COMPLETE',rid,len(rows),flush=True)

def tests(rid,home):
    old,_=inputs(home);family=MAP[rid]
    stream([sys.executable,str(old/'run_service.py'),'tests','--round',family],old,OUT/f'round{rid}/tests_existing.log',45)
    stream([sys.executable,'-m','unittest','discover','-s',str(BASE/'tests'),'-p',f'test_round{rid}.py','-v'],BASE,OUT/f'round{rid}/tests_additional.log',30)
    write(OUT/f'round{rid}/tests.json',{'status':'PASSED','utc':utc(),'existing_test_receipt':read(old/f'outputs/round{family}/tests.json'),
          'new_test_scope':'relative feature contracts; see log','new_test_source_sha256':sha(BASE/'tests'/f'test_round{rid}.py'),
          'relative_source_sha256':sha(BASE/'relative_features.py')})

def pair(rid,home):
    old,expected=inputs(home);family=MAP[rid]
    t=read(OUT/f'round{rid}/tests.json')
    if t['status']!='PASSED' or t['relative_source_sha256']!=sha(BASE/'relative_features.py') or t['new_test_source_sha256']!=sha(BASE/'tests'/f'test_round{rid}.py'):
        raise ValueError('Current local test receipt required')
    # The prior supervisor refuses FAILED/RUNNING attempts and verifies completed stages.
    report=f'outputs/round{family}/screen/report.json'
    stream([sys.executable,str(old/'run_service.py'),'pair','--round',family,'--block','1',
            '--reviewed-screen',expected['paths'][report],'--home',str(home)],old,
            OUT/f'round{rid}/pair1.log',195)
    folder=old/f'outputs/round{family}/pair1';r=read(folder/'report.json');s=read(folder/'status.json')
    if s['status']!='COMPLETED' or s['report_sha256']!=sha(folder/'report.json'):
        raise ValueError('Pair completion receipt missing or mismatched')
    for n,h in r.get('output_sha256',{}).items():
        if sha(folder/n)!=h:raise ValueError('Pair artifact mismatch: '+n)
    if sha(old/'outputs/shared_controls/b1.json.gz')!=r['shared_control_sha256']:
        raise ValueError('Shared control checksum mismatch')
    write(OUT/f'round{rid}/endpoint_review.json',{'status':'ONE_PAIRED_BLOCK_COMPLETE','round':rid,'prior_family':family,
        'completed_pairs':1,'comparison':r.get('comparison'),'new_games_this_invocation':r.get('new_games'),
        'all_actor_callback_max_ms':r.get('all_actors_callback_max_ms'),'candidate_callback_max_ms':r.get('candidate_callback_max_ms'),
        'automatic_promotion':False,'official_submission_score':None,'later_blocks_authorized':False,
        'source_report_sha256':sha(folder/'report.json')})
    print('ONE_PAIRED_BLOCK_COMPLETE',rid,r.get('decision'),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['verify','analyze','tests','pair']);p.add_argument('--round',choices=MAP,default='21');p.add_argument('--home',type=Path,default=Path.home());a=p.parse_args()
    try:
        if a.command=='verify':inputs(a.home);print('REVIEWED_SCREENS_VERIFIED')
        else:globals()[a.command](a.round,a.home)
    except BaseException as e:
        write(OUT/f'round{a.round}/failure_{a.command}.json',{'utc':utc(),'type':type(e).__name__,'message':str(e)});raise
if __name__=='__main__':main()
