"""Bounded local-only feature investigation. No installs, cloud launches or Git writes."""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
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

BASE=Path(__file__).resolve().parent
OUT=BASE/'outputs'
PREVIOUS=Path.home()/'kaggriculture_workforce_milestone'
RESUME=Path.home()/'kaggriculture_manual_resume'
COMMIT='7194116dfc92a8663139611233b5a221dad431a4'
ENGINE_HASH='bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e'
STATUS='ACTION_FEATURE_AUDIT_PASSED'

def utc(): return datetime.now(timezone.utc).isoformat()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(x): return hashlib.sha256(canonical(x)).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def contained(root,relative):
    p=(Path(root)/relative).resolve()
    if not p.is_relative_to(Path(root).resolve()): raise ValueError('Escaping artifact path')
    return p
def write_bytes(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.checkpoint-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
def write(p,x): write_bytes(p,json.dumps(x,indent=2,sort_keys=True,allow_nan=False).encode()+b'\n')
def code_hash():
    return digest({str(p.relative_to(BASE)):sha(p) for p in sorted(BASE.rglob('*.py')) if 'outputs' not in p.parts})
def log(stage,**kw):
    OUT.mkdir(exist_ok=True)
    row={'utc':utc(),'stage':stage,**kw}
    with (OUT/'events.jsonl').open('a') as f:f.write(json.dumps(row)+'\n');f.flush()
    print(json.dumps(row),flush=True)
def save_cache(path,fp,payload):
    obj={'fingerprint':fp,'payload':payload};obj['checksum']=digest(obj)
    write_bytes(path,gzip.compress(canonical(obj),mtime=0))
def load_cache(path,fp):
    if not Path(path).exists():return None
    obj=json.loads(gzip.decompress(Path(path).read_bytes())); checksum=obj.pop('checksum')
    if digest(obj)!=checksum:raise ValueError('Cache checksum mismatch; preserve and investigate')
    if obj['fingerprint']!=fp:raise ValueError('Different code/input checkpoint; no automatic overwrite')
    return obj['payload']

def runtime_executable(resume):
    r=read(resume/'state/runtime.json')
    if r['status']!='PASSED':raise ValueError('Previous runtime was not verified')
    return Path(r['executable'])

def validate_previous_code(previous):
    expected=read(BASE/'reference/previous_code_manifest.json')
    for rel,h in expected.items():
        if sha(contained(previous,rel))!=h:raise ValueError('Notebook-06 source changed: '+rel)

def prior_state(previous):
    """Return passed/never_run; a prior failure or partial attempt must be diagnosed."""
    out=previous/'outputs'
    if (out/'run_status.json').exists():
        r=read(out/'run_status.json')
        if r.get('status')=='PASSED': return 'passed'
        raise RuntimeError('Notebook 06 has a failed/interrupted/active run. Bundle it; do not retry unchanged.')
    if (out/'failure.json').exists() or (out/'report.json').exists() or list(out.glob('checkpoints/*')):
        raise RuntimeError('Notebook 06 has incomplete evidence without a passed receipt. Bundle it for review.')
    return 'never_run'

def verify_previous(previous,resume):
    validate_previous_code(previous)
    if prior_state(previous)!='passed':raise RuntimeError('Run ensure06 first')
    command=[str(runtime_executable(resume)),str(previous/'run_milestone.py'),'verify']
    result=subprocess.run(command,cwd=previous,text=True,capture_output=True,timeout=25,
                          env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    if result.returncode:raise RuntimeError('Notebook-06 verification failed: '+result.stderr[-3000:])
    r=json.loads(result.stdout)
    state=read(previous/'outputs/run_status.json')
    if state['report_sha256']!=sha(previous/'outputs/report.json'):raise ValueError('Notebook-06 final receipt hash differs')
    if r['status']!='WORKFORCE_COVERAGE_PASSED' or r['source_commit']!=COMMIT:raise ValueError('Wrong notebook-06 result')
    if r['source_episodes']!=7 or r['saved_observations']!=161:raise ValueError('Unexpected prior evidence scope')
    return r

def supervise(command,seconds,cwd,stage):
    """Child process group, 10-second heartbeat, hard timeout plus 2-second kill grace."""
    log(stage+'_STARTED',hard_limit_seconds=seconds)
    started=time.monotonic();last=started
    child=subprocess.Popen(command,cwd=cwd,start_new_session=True,
                           env={**os.environ,'PYTHONUNBUFFERED':'1','PYTHONDONTWRITEBYTECODE':'1'})
    try:
        while child.poll() is None:
            now=time.monotonic()
            if now-started>=seconds:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=2)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                raise TimeoutError(stage+' stopped at its hard budget; checkpoints preserved')
            if now-last>=10:log(stage+'_HEARTBEAT',elapsed_seconds=round(now-started,1));last=now
            time.sleep(.1)
    except BaseException:
        if child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
        raise
    if child.returncode:raise RuntimeError(stage+f' failed (exit {child.returncode}); inspect saved diagnostics')

def ensure06(args):
    validate_previous_code(args.previous)
    state=prior_state(args.previous)
    if state=='never_run':
        # Explicit user-run stage only; never launched on import or while opening the notebook.
        supervise([str(runtime_executable(args.resume)),str(args.previous/'run_milestone.py'),
                   'run','--seconds','180'],195,args.previous,'NOTEBOOK06')
    report=verify_previous(args.previous,args.resume)
    receipt={'status':'PASSED','utc':utc(),'reused_existing_pass':state=='passed',
             'previous_report_sha256':sha(args.previous/'outputs/report.json'),
             'source_commit':report['source_commit'],'previous_saved_observations':report['saved_observations']}
    write(OUT/'prerequisite.json',receipt);log('NOTEBOOK06_GATE_PASSED',reused=state=='passed')

def preflight(args):
    verify_previous(args.previous,args.resume)
    source=read(args.resume/'state/source.json');ready=read(args.resume/'state/readiness.json')
    restored=read(args.resume/'state/restore.json');runtime=read(args.resume/'state/runtime.json')
    repo=Path(source['repo']).resolve()
    if source['status']!='PASSED' or source['head']!=COMMIT or restored['status']!='PASSED':raise ValueError('Prior setup source/status mismatch')
    if sys.version_info[:2]!=(3,12) or Path(sys.executable).absolute()!=Path(runtime['executable']).absolute():
        raise ValueError('Use Kaggriculture Manual (verified source), not system Python')
    def git(*parts):return subprocess.check_output(['git',*parts],cwd=repo,text=True,timeout=10).strip()
    if git('rev-parse','HEAD')!=COMMIT:raise ValueError('Checkout changed; do not reset it')
    if git('status','--porcelain','--untracked-files=no'):raise ValueError('Tracked changes exist; preserve and inspect')
    for rel,h in ready['source_files'].items():
        if sha(contained(repo,rel))!=h:raise ValueError('Source mismatch '+rel)
    sys.path.insert(0,str(repo/'src'))
    from kaggriculture_research import environment
    if not Path(environment.__file__).resolve().is_relative_to(repo/'src'):raise ValueError('Wrong source import')
    manifest=environment.engine_manifest()
    if manifest['files']['envs/kaggriculture/kaggriculture.py']!=ENGINE_HASH:raise ValueError('Engine mismatch')
    root=Path(restored['private_root']).resolve()
    if restored['episode_count']!=7 or len(restored['downloaded_or_reused'])!=10:raise ValueError('Wrong recovery scope')
    for entry in restored['downloaded_or_reused']:
        p=contained(root,entry['path'])
        if p.stat().st_size!=entry['bytes'] or sha(p)!=entry['sha256']:raise ValueError('Evidence changed '+str(p))
    receipt={'status':'PASSED','utc':utc(),'source_commit':COMMIT,'repo':str(repo),
             'engine_sha256':ENGINE_HASH,'code_sha256':code_hash(),'private_root':str(root),
             'previous_report_sha256':sha(args.previous/'outputs/report.json'),'verified_objects':10}
    write(OUT/'preflight.json',receipt);log('PREFLIGHT_PASSED',verified_objects=10)
    return root,environment,receipt

def unit_tests():
    suite=unittest.defaultTestLoader.discover(str(BASE/'tests'))
    result=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
    receipt={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)}
    write(OUT/'tests.json',receipt)
    if not result.wasSuccessful() or result.skipped:raise RuntimeError('Tests failed/skipped')
    return receipt

def differential(observation,candidate,game):
    """Copied observation only, exact unit actions and decay; no hidden state or full game.

    Market held fixed until final liquidation for this CONDITIONAL parity test.
    No claim is made about the real future market or other workers' actions.
    """
    from opportunity_features import sale_prefix
    idx=candidate['worker_index'];steps=candidate['plan']
    if not candidate['within_deadline'] or candidate['kind']=='pass':return None
    farm=deepcopy(observation['farms'][observation['player']]);private=deepcopy(observation['private'])
    market=deepcopy(observation['market']);base_shed=deepcopy(private['shed'])
    before=sum(sale_prefix(game.market_price,item,market['inventory'][item],n)[0]
               for item,n in base_shed.items() if item in game.PRODUCTS)
    step=observation['day']*24+observation['hour']
    for delay,op in enumerate(steps):
        game._apply_unit_action(farm,private,idx,[op],10,29,24,100)
        game._decay_plants(farm,step+delay)
    deposited=sum(private['shed'].values())-sum(base_shed.values())
    initial_cash=farm['money']
    for item in game.PRODUCTS:
        n=private['shed'].get(item,0)
        for _ in range(n):
            p=game.market_price(item,market['inventory'][item])
            if not game._commit_unit('SELL',item,p,farm,private,market,100):raise ValueError('Official sale failed')
    measured=farm['money']-initial_cash-before
    if deposited!=candidate['accepted_units'] or not math_close(measured,candidate['frozen_bundle_revenue']):
        raise ValueError('Official primitive parity failed: '+candidate['candidate_id'])
    return {'candidate_id':candidate['candidate_id'],'accepted_units':deposited,
            'measured_incremental_frozen_revenue':measured,'primitive_action_steps':len(steps),'passed':True}

def math_close(a,b):return abs(a-b)<1e-7

def mechanics(game):
    """Six synthetic mechanics states, explicitly not earned episodes or scoring evidence."""
    from opportunity_features import Rules,extract_opportunities
    rows=[]
    for case in range(6):
        farms=[game._new_farm(10,3000) for _ in range(2)]
        private=game._new_private();hour=22 if case==0 else (21 if case==1 else 0)
        private['shed']={'WHEAT':5};farms[0]['tiles'][4][4]=game._new_plant('WHEAT',26,24)
        farms[0]['tiles'][4][4]['yield_units']=4
        if case==0:private['inventories'][0]={'WHEAT':3}
        if case==2:
            farms[0]['farmer']=[0,0];farms[0]['tiles'][4][4]=None
            farms[0]['tiles'][0][2]=game._new_plant('WHEAT',24,24)
            farms[0]['tiles'][0][2]['yield_units']=6
        if case==3:
            private['shed']={'FERTILIZER':94};private['inventories'][0]={'WHEAT':3,'MILK':5}
        if case==4:
            private['shed']={'FERTILIZER':93};private['inventories'][0]={'WHEAT':1,'MILK':5}
        if case==5:
            farms[0]['hands']=[[4,4] for _ in range(12)];farms[0]['hires_today']=12
            private['inventories']=[{} for _ in range(13)]
        obs={'player':0,'day':29,'hour':hour,'step':696+hour,'farms':farms,'private':private,
             'market':game._new_market(),'town':game._new_town()}
        result=extract_opportunities(obs,Rules.from_game(game)); checked=0
        for candidate in result.candidates:
            if candidate['kind']!='pass' and candidate['within_deadline']:
                parity=differential(obs,candidate,game)
                rows.append({'source':'synthetic_mechanics','case':case,**parity});checked+=1
                if checked==2:break
        if not checked:raise ValueError('Mechanics case had no tested candidate')
    return rows

def replay(root,environment,fp):
    from opportunity_features import Rules,extract_opportunities
    from kaggriculture_research.artifacts import load_checkpoint
    from kaggriculture_staffing.experiment import validate_episode
    progress=read(root/'reports/staffing_progress.json')
    if progress['completed_games']!=7 or progress['complete']:raise ValueError('Wrong pilot scope')
    artifacts=progress['artifact_manifest']
    if len(artifacts)!=7 or len({a['path'] for a in artifacts})!=7:raise ValueError('Duplicate/missing episodes')
    episodes=[]
    for i,artifact in enumerate(artifacts,1):
        key={k:artifact[k] for k in ('seed','seat','opponent','arm')};episode_id=digest(key)[:20]
        path=contained(root,artifact['path'])
        if sha(path)!=artifact['sha256']:raise ValueError('Episode hash mismatch')
        episode_fp=digest({'run':fp,'key':key,'source_sha256':artifact['sha256']})
        checkpoint=OUT/'checkpoints'/f'episode-{episode_id}.json.gz'
        saved=load_cache(checkpoint,episode_fp)
        if saved is not None:
            episodes.append(saved);log('EPISODE_REUSED',episode=i,total=7);continue
        payload=load_checkpoint(path,{**progress['lineage'],**key})
        if payload is None:raise ValueError('Episode lineage mismatch')
        validate_episode(payload,key)
        states=[];candidates=[];choices=[];parities=[];seen=set();example=None
        for record in payload['records']:
            if record['player']!=key['seat'] or record['observation']['day']!=29:continue
            obs=record['observation'];before=deepcopy(obs);step=obs['day']*24+obs['hour']
            if step in seen:raise ValueError('Duplicate episode/seat/step')
            seen.add(step);tick=time.perf_counter()
            result=extract_opportunities(obs,Rules.from_game(environment.game))
            latency=(time.perf_counter()-tick)*1000
            if obs!=before:raise ValueError('Input observation mutated')
            meta={**key,'episode_id':episode_id,'step':step}
            states.append({**meta,**result.state,'extractor_ms':latency})
            candidates.extend({**meta,**c} for c in result.candidates)
            choices.extend({**meta,'source_arm':key['arm'],**c} for c in result.choices)
            if example is None or len(result.candidates)>len(example['candidates']):
                example={'metadata':meta,'candidates':result.candidates,'choices':result.choices,'state':result.state}
            for c in result.candidates:
                if len(parities)>=3:break
                if c['kind']!='pass' and c['within_deadline']:
                    p=differential(obs,c,environment.game)
                    parities.append({'source':'saved_observation','step':step,'episode_id':episode_id,**p})
        if len(states)!=23:raise ValueError('Expected 23 final-day observations per accepted episode')
        saved={'key':key,'states':states,'candidates':candidates,'choices':choices,'parities':parities,'example':example}
        save_cache(checkpoint,episode_fp,saved);episodes.append(saved)
        log('EPISODE_CHECKPOINTED',episode=i,total=7,observations=len(states),candidate_rows=len(candidates))
    if sum(len(e['states']) for e in episodes)!=161:raise ValueError('Expected 161 observations')
    return episodes

def atomic_csv(path,frame,compressed=False):
    data=frame.to_csv(index=False).encode()
    write_bytes(path,gzip.compress(data,mtime=0) if compressed else data)

def summarize(episodes,parities,pf,tests,fp,started,mode='AWS_SAVED_OBSERVATIONS'):
    import pandas as pd
    from opportunity_features import ARMS,SCHEMA
    states=pd.DataFrame([r for e in episodes for r in e['states']])
    candidates=pd.DataFrame([r for e in episodes for r in e['candidates']])
    choices=pd.DataFrame([r for e in episodes for r in e['choices']])
    pairs=pd.DataFrame(parities+[r for e in episodes for r in e['parities']],
        columns=['source','case','episode_id','step','candidate_id','accepted_units',
                 'measured_incremental_frozen_revenue','primitive_action_steps','passed'])
    if mode=='AWS_SAVED_OBSERVATIONS' and (pairs.empty or not pairs.passed.all()):
        raise ValueError('Live audit requires passed official primitive-mechanics checks')
    # Group first within episodes, then seed/opponent blocks. No turn-level inference.
    group_cols=['seed','seat','opponent','arm']
    # The episode source arm and probe arm must be distinct; replay preserves source_arm below.
    grouped=choices.groupby(['episode_id','seed','seat','opponent','source_arm','arm'],dropna=False).agg(
        evaluated_worker_states=('worker_index','size'),changed_first_actions=('changed_first_action','sum'),
        changed_tasks=('changed_task','sum')).reset_index()
    grouped['first_action_change_fraction']=grouped.changed_first_actions/grouped.evaluated_worker_states
    block=grouped.groupby(['seed','opponent','arm']).agg(
        observed_episodes=('episode_id','nunique'),mean_episode_action_change_fraction=('first_action_change_fraction','mean')).reset_index()
    numeric=[c for c in candidates.select_dtypes(include='number').columns if c not in ('seed','seat','step','worker_index')]
    registry=[]
    for column in numeric:
        registry.append({'feature':column,'distinct_values':int(candidates[column].nunique()),
                         'nonzero_fraction':float((candidates[column]!=0).mean()),
                         'episodes_with_variation':int((candidates.groupby('episode_id')[column].nunique()>1).sum()),
                         'status':'candidate_not_outcome_ablated'})
    exports={'state_features.csv':states,'candidate_features.csv.gz':candidates.drop(columns=['plan']),
             'probe_choices.csv.gz':choices,'probe_by_episode.csv':grouped,
             'probe_by_block.csv':block,'feature_registry.csv':pd.DataFrame(registry),'mechanics_parity.csv':pairs}
    for name,frame in exports.items():atomic_csv(OUT/name,frame,compressed=name.endswith('.gz'))
    example=max((e['example'] for e in episodes),key=lambda e:len(e['candidates']))
    write(OUT/'example_state.json',example)
    r={'status':STATUS if mode=='AWS_SAVED_OBSERVATIONS' else 'SYNTHETIC_DEMO_ONLY',
       'execution_mode':mode,'utc':utc(),'schema':SCHEMA,'fingerprint':fp,'code_sha256':code_hash(),
       'source_commit':COMMIT,'engine_sha256':pf.get('engine_sha256'),'tests':tests,
       'source_episodes':len(episodes),'saved_observations':len(states),'candidate_rows':len(candidates),
       'numeric_candidate_descriptors':len(numeric),'aggregate_state_descriptors':14,'probe_diagnostic_columns':8,
       'varying_candidate_descriptors':sum(x['distinct_values']>1 for x in registry),
       'primitive_parity_checks':len(pairs),'primitive_action_steps':int(pairs.primitive_action_steps.sum()) if len(pairs) else 0,
       'primitive_parity_passed':bool(pairs.passed.all()) if len(pairs) else False,
       'new_complete_games':0,'models_fit':0,'validation_or_holdout_used':False,
       'frozen_policy_modified':False,'full_callback_acceptance':'NOT_RUN',
       'official_metric_effect_measured':False,'official_submission_score':None,
       'feature_value_proven':False,'feature_completion_gate':'OPEN','github_updated':False,
       'elapsed_seconds':time.monotonic()-started,
       'extractor_ms':{'median':float(states.extractor_ms.median()),'p95':float(states.extractor_ms.quantile(.95)),'max':float(states.extractor_ms.max())},
       'timing_scope':'Feature construction only; cached episodes retain prior timing; not full agent callback',
       'probe_scope':'Unexecuted independent-worker candidate ranking probes; NOT game-outcome ablations',
       'next_gate':'Inspect action activation, then integrate one family under equal rules and measure full callback before paired games',
       'limitations':['Seven accepted episodes from latency-censored eight-game pilot; not fresh validation.',
           'Final day only; no overnight refresh, new purchases, water/feed/investment actions or future-production claims.',
           'Frozen-market scenarios do not predict actual town demand or simultaneous rival trades.',
           'Manual DROP only; current shed held unchanged until drop; inventory iteration order follows supplied observation.',
           'Independent workers can select conflicting tasks or exceed shared capacity; no joint revenue or stronger agent claim.',
           'One deterministic shortest path per option; same first-command alternatives are grouped for action regret.'],
       'output_sha256':{name:sha(OUT/name) for name in [*exports,'example_state.json']}}
    write(OUT/'report.json',r);log(r['status'],observations=len(states),candidate_rows=len(candidates))
    return r

def worker(args):
    started=time.monotonic();test_result=unit_tests();root,environment,pf=preflight(args)
    fp=digest({'code':code_hash(),'prior':pf['previous_report_sha256'],'progress':sha(root/'reports/staffing_progress.json')})
    parities=mechanics(environment.game)
    write(OUT/'mechanics_progress.json',parities)
    episodes=replay(root,environment,fp)
    # Disambiguate the frozen source arm from the candidate probe's arm.
    for e in episodes:
        for row in e['choices']:row['source_arm']=e['key']['arm']
    summarize(episodes,parities,pf,test_result,fp,started)

def verify():
    report=read(OUT/'report.json');state=read(OUT/'run_status.json')
    if report['status']!=STATUS or report['code_sha256']!=code_hash():raise ValueError('Report status/code mismatch')
    if state['status']!='PASSED' or state['report_sha256']!=sha(OUT/'report.json'):raise ValueError('No matching final run receipt')
    for rel,h in report['output_sha256'].items():
        if sha(contained(OUT,rel))!=h:raise ValueError('Export hash mismatch: '+rel)
    return report

def run(args):
    import fcntl
    OUT.mkdir(exist_ok=True)
    with (OUT/'.run.lock').open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another notebook-07 process is active')
        if (OUT/'run_status.json').exists():
            old=read(OUT/'run_status.json')
            if old['status']=='PASSED':
                preflight(args);verify();log('EXISTING_PASS_REUSED');return
            if not args.resume_after_review:raise RuntimeError('Prior attempt needs diagnosis. Bundle it; no automatic unchanged retry.')
        write(OUT/'run_status.json',{'status':'RUNNING','utc':utc()})
        supervise([sys.executable,str(BASE/'run_next.py'),'_worker','--previous',str(args.previous),
                   '--resume',str(args.resume)],args.seconds,BASE,'NOTEBOOK07')
        report=read(OUT/'report.json')
        if report['status']!=STATUS:raise ValueError('No completed audit result')
        write(OUT/'run_status.json',{'status':'PASSED','utc':utc(),'report_sha256':sha(OUT/'report.json')})
        verify();log('NOTEBOOK07_COMPLETE')

def bundle(args):
    """Always usable after failure; includes derived results, never raw input episodes."""
    OUT.mkdir(exist_ok=True)
    archive=BASE/'kaggriculture_action_feature_results.zip'
    known=['report.json','preflight.json','prerequisite.json','tests.json','failure.json',
           'failure_worker.json','run_status.json','mechanics_progress.json','events.jsonl',
           'state_features.csv','candidate_features.csv.gz','probe_choices.csv.gz',
           'probe_by_episode.csv','probe_by_block.csv','feature_registry.csv',
           'mechanics_parity.csv','example_state.json','action_opportunities.html']
    chosen=[OUT/name for name in known]+list((OUT/'checkpoints').glob('episode-*.json.gz'))
    paths=[(p,'outputs/'+str(p.relative_to(OUT))) for p in chosen if p.is_file() and not p.is_symlink()]
    paths += [(p,p.name) for p in BASE.glob('07_*.ipynb')]
    for name in ('report.json','failure.json','run_status.json','tests.json','preflight.json'):
        p=args.previous/'outputs'/name
        if p.is_file():paths.append((p,'previous06/'+name))
    paths += [(p,'reference/'+p.name) for p in (BASE/'reference').glob('*.json')]
    manifest={name:sha(p) for p,name in paths}
    tmp=archive.with_suffix('.tmp')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for p,name in paths:z.write(p,name)
        z.writestr('BUNDLE_MANIFEST.json',json.dumps({'utc':utc(),'files':manifest,'raw_input_episodes_included':False},indent=2))
    os.replace(tmp,archive)
    print('UPLOAD THIS RESULTS FILE:',archive,flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['ensure06','run','_worker','verify','bundle'])
    parser.add_argument('--previous',type=Path,default=PREVIOUS)
    parser.add_argument('--resume',type=Path,default=RESUME)
    parser.add_argument('--seconds',type=int,default=180)
    parser.add_argument('--resume-after-review',action='store_true',help='Only after diagnosing an interruption; hashes still must match')
    args=parser.parse_args()
    if not 30<=args.seconds<=180:parser.error('Budget must be 30..180 seconds')
    try:
        if args.stage=='ensure06':ensure06(args)
        elif args.stage=='run':run(args)
        elif args.stage=='_worker':worker(args)
        elif args.stage=='verify':print(json.dumps(verify(),indent=2))
        else:bundle(args)
    except BaseException as exc:
        if args.stage!='bundle':
            write(OUT/('failure_worker.json' if args.stage=='_worker' else 'failure.json'),{'utc':utc(),'stage':args.stage,'error':str(exc),'type':type(exc).__name__,
                                    'traceback':traceback.format_exc(),'checkpoints_preserved':True})
            if args.stage=='run':write(OUT/'run_status.json',{'status':'FAILED','utc':utc()})
        raise

if __name__=='__main__':main()
