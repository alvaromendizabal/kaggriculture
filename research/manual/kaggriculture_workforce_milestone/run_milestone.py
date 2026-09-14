"""Bounded, restartable, local-only workforce audit. No cloud or Git writes."""
from __future__ import annotations
import argparse
import contextlib
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import unittest
import zipfile

BASE = Path(__file__).resolve().parent
OUT = BASE / "outputs"
COMMIT = "7194116dfc92a8663139611233b5a221dad431a4"
ENGINE_HASH = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
STATE_STATUS = "WORKFORCE_COVERAGE_PASSED"
REPO_DEFAULT = Path.home()/"projects/kaggriculture-manual"
RESUME_DEFAULT = Path.home()/"kaggriculture_manual_resume"


def utc():return datetime.now(timezone.utc).isoformat()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(",", ":"),allow_nan=False).encode()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())

def write(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.checkpoint-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(json.dumps(value,indent=2,sort_keys=True,allow_nan=False).encode()+b'\n')
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def log(stage, **fields):
    row={'utc':utc(),'stage':stage,**fields}
    OUT.mkdir(exist_ok=True)
    with (OUT/'events.jsonl').open('a') as f:f.write(json.dumps(row,sort_keys=True)+'\n');f.flush()
    print(json.dumps(row,sort_keys=True),flush=True)

def command(args,cwd):
    return subprocess.check_output(args,cwd=cwd,text=True,timeout=10).strip()

def contained(root,path):
    root=Path(root).resolve();p=(root/path).resolve()
    if not p.is_relative_to(root):raise ValueError(f'Path escapes evidence root: {path}')
    return p

def code_digest():
    return digest({str(p.relative_to(BASE)):sha(p) for p in sorted(BASE.rglob('*.py')) if 'outputs' not in p.parts})

def save_cache(path, fingerprint, payload):
    envelope={'fingerprint':fingerprint,'payload':payload}
    envelope['checksum']=digest(envelope);write(path,envelope)

def read_cache(path,fingerprint):
    if not Path(path).exists():return None
    x=read(path);checksum=x.pop('checksum',None)
    if checksum!=digest(x):raise ValueError(f'Output checkpoint checksum changed: {path}')
    if x['fingerprint']!=fingerprint:
        raise ValueError('Checkpoint belongs to different source/input; preserve it and inspect before rerunning')
    return x['payload']

def tests():
    suite=unittest.defaultTestLoader.discover(str(BASE/'tests'),pattern='test_*.py')
    result=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
    receipt={'utc':utc(),'tests_run':result.testsRun,'failures':len(result.failures),
             'errors':len(result.errors),'skips':len(result.skipped),'status':'PASSED' if result.wasSuccessful() else 'FAILED'}
    write(OUT/'tests.json',receipt)
    if not result.wasSuccessful() or result.skipped:raise RuntimeError('Tests failed or skipped')
    return receipt

def preflight(repo,resume):
    repo=repo.resolve();resume=resume.resolve()
    source=read(resume/'state/source.json');runtime=read(resume/'state/runtime.json')
    readiness=read(resume/'state/readiness.json');restore=read(resume/'state/restore.json')
    if source['head']!=COMMIT or readiness['source_commit']!=COMMIT:raise ValueError('Readiness source changed')
    if source['status']!='PASSED' or runtime['status']!='PASSED' or restore['status']!='PASSED':raise ValueError('Readiness stage not passed')
    if command(['git','rev-parse','HEAD'],repo)!=COMMIT:raise ValueError('Checkout HEAD differs; do not reset automatically')
    if command(['git','status','--porcelain','--untracked-files=no'],repo):raise ValueError('Tracked checkout changes exist; preserving them; stop for review')
    if Path(source['repo']).resolve()!=repo:raise ValueError('Wrong repository path')
    if sys.version_info[:2]!=(3,12):raise ValueError('Use the verified Python 3.12 kernel, not system Python')
    if Path(sys.executable).absolute()!=Path(runtime['executable']).absolute():
        raise ValueError(f'Use existing verified interpreter: {runtime["executable"]}')
    for relative,expected in readiness['source_files'].items():
        if sha(repo/relative)!=expected:raise ValueError(f'Source file changed: {relative}')
    sys.path.insert(0,str(repo/'src'))
    from kaggriculture_research import environment
    if not Path(environment.__file__).resolve().is_relative_to(repo/'src'):
        raise ValueError('Import resolves to old workspace')
    engine=environment.engine_manifest()
    if engine['files']['envs/kaggriculture/kaggriculture.py']!=ENGINE_HASH:
        raise ValueError('Pinned engine hash changed')
    root=Path(restore['private_root']).resolve()
    restored=restore['downloaded_or_reused']
    if len(restored)!=10 or restore['episode_count']!=7:raise ValueError('Unexpected recovery scope')
    for i,item in enumerate(restored):
        p=contained(root,item['path'])
        if p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:
            raise ValueError(f'Restored evidence changed: {p}')
    receipt={'status':'PASSED','utc':utc(),'source_commit':COMMIT,'repo':str(repo),
             'python':sys.version.split()[0],'engine':engine,'private_root':str(root),
             'verified_objects':10,'raw_data_redownloaded':False,'code_sha256':code_digest()}
    write(OUT/'preflight.json',receipt)
    log('PREFLIGHT_PASSED',verified_objects=10)
    return root,environment,receipt

def mechanics(environment,fingerprint):
    from copy import deepcopy
    from workforce_features import Rules,extract_workforce
    from kaggriculture_research.market_features import project_observation
    rules=Rules.from_game(environment.game)
    cache=OUT/'checkpoints/mechanics.json'
    saved=read_cache(cache,fingerprint)
    if saved is not None:
        log('MECHANICS_CACHE_REUSED',views=len(saved['rows']));return saved
    rows=[];snapshots=[];transitions=0
    for hiring_player in (0,1):
        env=environment.make_environment(0)
        starting=float(env.state[hiring_player].observation.farms[hiring_player]['money'])
        for amount in (0,4,8):
            if amount:
                actions=[]
                for player in (0,1):
                    f=env.state[player].observation.farms[player]
                    actions.append({'farmer':['PASS'],'hands':[['PASS'] for _ in f['hands']],
                                    'market':[['HIRE'] for _ in range(amount)] if player==hiring_player else []})
                env.step(actions);transitions+=1
            n=len(env.state[hiring_player].observation.farms[hiring_player]['hands'])
            expected={0:0,4:4,8:12}[amount]
            if n!=expected:raise ValueError(f'Engine fixture workforce changed: {n} != {expected}')
            for viewer in (0,1):
                obs=dict(env.state[viewer].observation);before=deepcopy(obs)
                tick=time.perf_counter();features=extract_workforce(obs,rules);ms=(time.perf_counter()-tick)*1000
                if obs!=before:raise ValueError('Extractor mutated engine observation')
                normalized={**obs,'step':int(obs['day'])*24+int(obs['hour'])}
                old_rejected=False;reason=None
                try:project_observation(normalized)
                except ValueError as error:
                    old_rejected=True;reason=str(error)
                row={'hiring_player':hiring_player,'viewer':viewer,'hired_hands':n,
                     'new_passed':True,'old_rejected':old_rejected,'old_reason':reason,
                     'own_worker_rows':sum(w['side']=='own' for w in features.workers),
                     'opponent_worker_rows':sum(w['side']=='opponent' for w in features.workers),
                     'extractor_ms':ms}
                rows.append(row)
                write(OUT/'mechanics_progress.json',{'fixture_transitions':transitions,'rows':rows})
                if old_rejected!=(n>3) or (old_rejected and 'at most three' not in reason):
                    raise ValueError('Unexpected frozen-validator behavior; saved result for review')
                snapshots.append({'label':f'fixture-hirer{hiring_player}-view{viewer}-hands{n}',
                                  'state':features.state,'workers':features.workers,'tasks':features.tasks})
            log('MECHANICS',hiring_player=hiring_player,hired_hands=n,views_completed=len(rows))
        cost=sum(environment.game._hire_cost(i) for i in range(12))
        if starting-float(env.state[hiring_player].observation.farms[hiring_player]['money'])!=cost:
            raise ValueError('Hire accounting mismatch')
    payload={'rows':rows,'snapshots':snapshots,'fixture_transitions':transitions,'full_games':0,
             'actual_maximum_workforce_claimed':False}
    save_cache(cache,fingerprint,payload);return payload

def replay(root,environment,fingerprint):
    from copy import deepcopy
    from workforce_features import Rules,extract_workforce
    from kaggriculture_research.artifacts import load_checkpoint
    from kaggriculture_staffing.experiment import validate_episode
    progress=read(root/'reports/staffing_progress.json')
    if progress['completed_games']!=7 or progress['complete']:
        raise ValueError('This milestone requires exactly the seven accepted pilot games')
    manifest=progress['artifact_manifest']
    if len(manifest)!=7:raise ValueError('Unexpected source manifest length')
    if len({a['path'] for a in manifest})!=7:raise ValueError('Duplicate episode in manifest')
    rules=Rules.from_game(environment.game);outputs=[]
    for number,artifact in enumerate(manifest,1):
        key={k:artifact[k] for k in ('seed','seat','opponent','arm')}
        path=contained(root,artifact['path'])
        if sha(path)!=artifact['sha256']:raise ValueError('Episode bytes changed')
        episode_fp=digest({'run':fingerprint,'key':key,'input_sha256':artifact['sha256']})
        cache=OUT/'checkpoints'/f'episode-{digest(key)[:20]}.json'
        saved=read_cache(cache,episode_fp)
        if saved is not None:
            outputs.append(saved);log('EPISODE_REUSED',episode=number,total=7,states=len(saved['states']));continue
        payload=load_checkpoint(path,{**progress['lineage'],**key})
        if payload is None:raise ValueError('Checkpoint lineage mismatch')
        validate_episode(payload,key)
        rows=[];workers=[];task_data=[];sample=None;seen=set()
        for record in payload['records']:
            if record['player']!=key['seat'] or record['observation']['day']!=29:continue
            obs=record['observation'];before=deepcopy(obs)
            tick=time.perf_counter();result=extract_workforce(obs,rules);ms=(time.perf_counter()-tick)*1000
            if obs!=before:raise ValueError('Extractor mutated saved observation')
            step=obs['day']*24+obs['hour']
            if step in seen:raise ValueError('Duplicate episode/seat/step')
            seen.add(step)
            meta={**key,'step':step,'episode_id':digest(key)[:20]}
            rows.append({**meta,'extractor_ms':ms,**result.state})
            workers.extend({**meta,**w} for w in result.workers)
            task_data.extend({**meta,**t} for t in result.tasks)
            if sample is None or len(result.tasks)>len(sample['tasks']):
                sample={'metadata':meta,'state':result.state,'workers':result.workers,'tasks':result.tasks}
        if len(rows)!=23:raise ValueError(f'Expected 23 accepted final-day decisions, got {len(rows)}')
        saved={'source_key':key,'source_sha256':artifact['sha256'],'states':rows,'workers':workers,
               'tasks':task_data,'example':sample}
        save_cache(cache,episode_fp,saved);outputs.append(saved)
        log('EPISODE_CHECKPOINTED',episode=number,total=7,states=len(rows))
    if sum(len(x['states']) for x in outputs)!=161:raise ValueError('Expected 161 saved observations')
    return outputs

def summarize(episodes,mechanics_result,preflight_result,test_result,fingerprint,started):
    import pandas as pd
    from workforce_features import SCHEMA_VERSION
    rows=[r for e in episodes for r in e['states']];frame=pd.DataFrame(rows)
    features=[k for k in rows[0] if k.startswith(('own.','opponent.','relative.','time.','own_inventory.'))]
    if len(features)!=124:raise ValueError('Aggregate feature schema drift')
    registry=[]
    for c in features:
        counts=frame.groupby('episode_id')[c].nunique()
        registry.append({'feature':c,'distinct_values':int(frame[c].nunique()),'nonzero_fraction':float((frame[c]!=0).mean()),
                         'minimum':float(frame[c].min()),'maximum':float(frame[c].max()),
                         'episodes_with_variation':int((counts>1).sum()),'status':'candidate_not_ablated'})
    workers=[r for e in episodes for r in e['workers']]
    tasks=[r for e in episodes for r in e['tasks']]
    for name,data in [('state_features.csv',rows),('worker_features.csv',workers),('task_features.csv',tasks),('feature_registry.csv',registry)]:
        # Derived exports are replaceable; durable source checkpoints remain checksummed.
        pd.DataFrame(data).to_csv(OUT/name,index=False)
    example=max((e['example'] for e in episodes),key=lambda x:len(x['tasks']))
    write(OUT/'example_state.json',example)
    receipt={'status':STATE_STATUS,'utc':utc(),'fingerprint':fingerprint,'schema':SCHEMA_VERSION,
             'source_commit':COMMIT,'code_sha256':preflight_result['code_sha256'],
             'tests':test_result,'source_episodes':7,'saved_observations':161,
             'aggregate_candidate_features':len(features),'varying_features':int((frame[features].nunique()>1).sum()),
             'worker_rows':len(workers),'task_rows':len(tasks),'mechanics_views':len(mechanics_result['rows']),
             'mechanics_fixture_transitions':4,'full_games_run':0,'new_training_runs':0,'models_fit':0,
             'feature_extractor_ms':{'median':float(frame.extractor_ms.median()),'p95':float(frame.extractor_ms.quantile(.95)),
                                     'max':float(frame.extractor_ms.max())},
             'full_callback_acceptance':'NOT_RUN','official_metric_effect_measured':False,
             'feature_selection_performed':False,'github_updated':False,'aws_resources_modified':False,
             'feature_completion_gate':'OPEN','elapsed_seconds_this_invocation':time.monotonic()-started,
             'timing_scope':'Only the new extractor; reused checkpoints retain original measurements; not complete policy latency',
             'next_step':'Integrate a forward-only action pathway, then bounded full-callback acceptance before new-game ablations',
             'output_sha256':{name:sha(OUT/name) for name in ['state_features.csv','worker_features.csv','task_features.csv','feature_registry.csv','example_state.json']}}
    write(OUT/'mechanics.json',mechanics_result)
    receipt['output_sha256']['mechanics.json']=sha(OUT/'mechanics.json')
    write(OUT/'report.json',receipt);log(STATE_STATUS,observations=161,features=len(features))
    return receipt

def worker(args):
    started=time.monotonic()
    try:
        test_result=tests()
        root,environment,pf=preflight(args.repo,args.resume)
        fingerprint=digest({'code':pf['code_sha256'],'source':COMMIT,'engine':pf['engine'],
                            'input_manifest':sha(root/'reports/staffing_progress.json')})
        mechanics_result=mechanics(environment,fingerprint)
        episodes=replay(root,environment,fingerprint)
        summarize(episodes,mechanics_result,pf,test_result,fingerprint,started)
    except Exception as error:
        write(OUT/'failure.json',{'status':'FAILED','utc':utc(),'error_type':type(error).__name__,
                                 'error':str(error),'traceback':traceback.format_exc(),
                                 'elapsed_seconds':time.monotonic()-started,'checkpoints_preserved':True})
        log('FAILED',error=str(error));raise

def run(args):
    OUT.mkdir(exist_ok=True)
    # Use an OS lock, automatically released after a crash; never run concurrent audits.
    import fcntl
    with (OUT/'.run.lock').open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another workforce audit is active')
        started=time.monotonic();log('RUN_STARTED',hard_limit_seconds=args.seconds)
        write(OUT/'run_status.json',{'status':'RUNNING','utc':utc(),'hard_limit_seconds':args.seconds})
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1')
        child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'_worker','--repo',str(args.repo),
                                '--resume',str(args.resume)],cwd=BASE,env=env,start_new_session=True)
        last=started
        try:
            while child.poll() is None:
                now=time.monotonic()
                if now-started>=args.seconds:
                    os.killpg(child.pid,signal.SIGTERM)
                    try:child.wait(timeout=2)
                    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                    write(OUT/'failure.json',{'status':'TIME_LIMIT','utc':utc(),'hard_limit_seconds':args.seconds,
                                             'elapsed_seconds':time.monotonic()-started,'checkpoints_preserved':True})
                    raise TimeoutError('Stopped at hard limit. Preserve outputs; diagnose before retrying.')
                if now-last>=10:log('HEARTBEAT',elapsed_seconds=round(now-started,1));last=now
                time.sleep(.2)
        except BaseException:
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGKILL);child.wait()
            write(OUT/'run_status.json',{'status':'FAILED_OR_INTERRUPTED','utc':utc()})
            raise
        if child.returncode:
            write(OUT/'run_status.json',{'status':'FAILED','utc':utc(),'returncode':child.returncode})
            raise RuntimeError('Audit failed; see outputs/failure.json. Do not run full historical studies.')
        report=verify_outputs()
        write(OUT/'run_status.json',{'status':'PASSED','utc':utc(),'report_sha256':sha(OUT/'report.json')})
        log('BOUNDED_RUN_COMPLETE',status=report['status'])

def verify_outputs():
    x=read(OUT/'report.json')
    if x['status']!=STATE_STATUS or x['code_sha256']!=code_digest():raise ValueError('Report source/status mismatch')
    for name,expected in x['output_sha256'].items():
        if sha(contained(OUT,name))!=expected:raise ValueError(f'Derived output changed: {name}')
    return x

def bundle():
    OUT.mkdir(exist_ok=True)
    archive=BASE/'kaggriculture_workforce_results.zip'
    paths=[p for p in OUT.rglob('*') if p.is_file() and p.name!='.run.lock' and p.suffix in ('.json','.jsonl','.csv','.html','.log')]
    paths += list(BASE.glob('06_*.ipynb'))
    paths += [p for p in (BASE/'reference').glob('*.json')]
    names={str(p.relative_to(BASE)):sha(p) for p in paths}
    with zipfile.ZipFile(archive.with_suffix('.tmp'), 'w', zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(BASE))
        z.writestr('BUNDLE_MANIFEST.json',json.dumps({'utc':utc(),'files':names,'no_raw_episodes_included':True},indent=2))
    os.replace(archive.with_suffix('.tmp'),archive)
    print('RESULTS_BUNDLE:',archive,flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['run','_worker','bundle','verify'])
    parser.add_argument('--repo',type=Path,default=REPO_DEFAULT)
    parser.add_argument('--resume',type=Path,default=RESUME_DEFAULT)
    parser.add_argument('--seconds',type=int,default=180)
    args=parser.parse_args()
    if not 30<=args.seconds<=180:parser.error('Budget must be 30..180 seconds')
    if args.stage=='run':run(args)
    elif args.stage=='_worker':worker(args)
    elif args.stage=='bundle':bundle()
    else:print(json.dumps(verify_outputs(),indent=2))

if __name__=='__main__':main()
