"""A single bounded recorded-action replay, never a policy experiment or cloud job."""
from __future__ import annotations
import argparse, gzip, json, os, signal, subprocess, sys, time, traceback, unittest, zipfile
from pathlib import Path
from artifact_io import read,sha,inside,write,atomic,digest,code_hash,save_cache,load_cache,utc
BASE=Path(__file__).resolve().parent
OUT=BASE/'outputs'
COMMIT='7194116dfc92a8663139611233b5a221dad431a4'
ENGINE='bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e'
CAP=120

def log(stage,**kwargs):
    OUT.mkdir(exist_ok=True); row={'utc':utc(),'stage':stage,**kwargs}
    with (OUT/'events.jsonl').open('a') as f: f.write(json.dumps(row,allow_nan=False)+'\n'); f.flush()
    print(json.dumps(row,allow_nan=False),flush=True)

def csv(path,rows):
    import pandas as pd
    data=pd.DataFrame(rows).to_csv(index=False).encode()
    atomic(path,gzip.compress(data,mtime=0) if str(path).endswith('.gz') else data)

def verify_package():
    manifest=read(BASE/'PACKAGE_MANIFEST.json')
    nb=read(BASE/'13_maintenance_loss_and_interaction_features.ipynb')
    body=[{'cell_type':c['cell_type'],'source':''.join(c['source']) if isinstance(c['source'],list) else c['source']} for c in nb['cells']]
    if digest(body)!=manifest['notebook_source_sha256']:
        raise ValueError('Notebook source changed; output saving is allowed')
    for name,h in manifest['files'].items():
        if sha(inside(BASE,name))!=h: raise ValueError('Package changed: '+name)

def preflight(home):
    from review_inputs import action_stream
    verify_package()
    prior=home/'kaggriculture_water_maintenance'
    hashes=read(BASE/'reference/input_hashes.json')
    streams=action_stream(prior,hashes)
    for stage in ('screen','pilot'):
        r=read(prior/f'outputs/{stage}/report.json'); status=read(prior/f'outputs/{stage}/status.json')
        if status['status']!='COMPLETED' or status['report_sha256']!=sha(prior/f'outputs/{stage}/report.json') or r['code_sha256']!=code_hash(prior):
            raise ValueError('Notebook12 status or code changed')
    old=home/'kaggriculture_manual_resume/state'
    source=read(old/'source.json'); runtime=read(old/'runtime.json'); restore=read(old/'restore.json'); ready=read(old/'readiness.json')
    if any(d.get('status')!='PASSED' for d in (source,runtime,restore)): raise ValueError('Missing prior readiness')
    if sys.version_info[:2]!=(3,12) or Path(sys.executable).absolute()!=Path(runtime['executable']).absolute(): raise ValueError('Select Kaggriculture Manual (verified source); no installation required')
    repo=Path(source['repo']).resolve()
    def git(*args): return subprocess.check_output(['git',*args],cwd=repo,text=True,timeout=10).strip()
    if git('rev-parse','HEAD')!=COMMIT or git('status','--porcelain','--untracked-files=no'): raise ValueError('Reviewed source changed; do not reset')
    for rel,h in ready['source_files'].items():
        if sha(inside(repo,rel))!=h: raise ValueError('Source differs: '+rel)
    sys.path.insert(0,str(repo/'src'))
    from kaggriculture_research import environment
    if not Path(environment.__file__).resolve().is_relative_to(repo/'src'): raise ValueError('Wrong source imports')
    if environment.engine_manifest()['files']['envs/kaggriculture/kaggriculture.py']!=ENGINE: raise ValueError('Pinned engine changed')
    root=Path(restore['private_root']).resolve()
    if restore['episode_count']!=7 or len(restore['downloaded_or_reused'])!=10: raise ValueError('Recovery scope differs')
    for obj in restore['downloaded_or_reused']:
        p=inside(root,obj['path'])
        if p.stat().st_size!=obj['bytes'] or sha(p)!=obj['sha256']: raise ValueError('Restored object changed')
    progress=read(root/'reports/staffing_progress.json')
    key=streams['control']['key']
    jobs=[a for a in progress['artifact_manifest'] if all(a[k]==v for k,v in key.items())]
    if len(jobs)!=1: raise ValueError('Selected source ambiguous')
    job=jobs[0]; path=inside(root,job['path'])
    from kaggriculture_research.artifacts import load_checkpoint
    if sha(path)!=job['sha256']: raise ValueError('Raw checkpoint differs')
    payload=load_checkpoint(path,{**progress['lineage'],**key})
    if payload is None: raise ValueError('Raw checkpoint lineage differs')
    fp=digest({'code':code_hash(BASE),'protocol':sha(BASE/'PROTOCOL.json'),'engine':ENGINE,'prior':hashes,'source':job['sha256']})
    write(OUT/'preflight.json',{'status':'PASSED','utc':utc(),'fingerprint':fp,'source_commit':COMMIT,'engine_sha256':ENGINE,'verified_objects':10,'prior_hashes':len(hashes),'source_key':key})
    log('PREFLIGHT_PASSED',verified_objects=10,recorded_actions=478)
    return payload,streams,environment,fp

def decomposition(branches):
    """Descriptive identity, not causal attribution of endogenous prices."""
    from collections import defaultdict
    tab=defaultdict(lambda:{'cash_control':0.,'cash_defer':0.,'units_control':0,'units_defer':0})
    for b in branches:
        for t in b['trades']:
            r=tab[(t['player'],t['operation'],t['item'])]
            r['cash_'+b['mode']]+=t['cash']; r['units_'+b['mode']]+=t['units']
    rows=[]
    for (player,op,item),r in sorted(tab.items()):
        out={'player':player,'operation':op,'item':item,**r,'cash_delta':r['cash_defer']-r['cash_control'],'units_delta':r['units_defer']-r['units_control']}
        out['quantity_component']=out['average_price_component']=None
        if op=='SELL' and r['units_control'] and r['units_defer']:
            q0,q1=r['units_control'],r['units_defer']; p0,p1=r['cash_control']/q0,r['cash_defer']/q1
            out['quantity_component']=(q1-q0)*(p0+p1)/2
            out['average_price_component']=(p1-p0)*(q0+q1)/2
            import math
            if not math.isclose(out['quantity_component']+out['average_price_component'],out['cash_delta'],abs_tol=1e-8): raise ValueError('Sales decomposition failed')
        rows.append(out)
    return rows

def test_suite():
    result=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(unittest.defaultTestLoader.discover(str(BASE/'tests')))
    r={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)}
    write(OUT/'tests.json',r)
    if not result.wasSuccessful() or result.skipped: raise RuntimeError('Tests failed or skipped')
    return r

def worker(home):
    start=time.monotonic(); tests=test_suite()
    source,streams,environment,fp=preflight(home)
    from mechanics_checks import validate
    mechanics=validate(environment.game); write(OUT/'mechanics.json',mechanics)
    log('MECHANICS_PASSED',component_scenarios=mechanics['component_scenarios'])
    from replay_diagnosis import replay_branch
    branches=[]; new_transitions=0
    for mode in ('control','defer'):
        path=OUT/'checkpoints'/f'{mode}.json.gz'; cpf=digest({'run':fp,'mode':mode})
        b=load_cache(path,cpf)
        if b is None:
            b=replay_branch(source,streams[mode],environment,log)
            save_cache(path,cpf,b); new_transitions+=719
            log('RECORDED_BRANCH_VERIFIED',mode=mode,rewards=b['rewards'])
        else: log('RECORDED_BRANCH_REUSED',mode=mode)
        branches.append(b)
    dec=decomposition(branches)
    for p in (0,1):
        expected=branches[1]['rewards'][p]-branches[0]['rewards'][p]
        if sum(r['cash_delta'] for r in dec if r['player']==p)!=expected: raise ValueError('Paired cash delta not reconciled')
    for filename,field in [('crop_features.csv.gz','plant_features'),('state_features.csv','state_features'),('trades.csv.gz','trades'),('crop_events.csv.gz','crop_events'),('cash.csv','cash')]:
        csv(OUT/filename,[r for b in branches for r in b[field]])
    csv(OUT/'cash_decomposition.csv',dec)
    from interaction_features import FIELDS
    rows=[r for b in branches for r in b['plant_features']]; reg=[]
    for field in FIELDS:
        vals=[r[field] for r in rows]
        reg.append({'feature':field,'distinct_values':len(set(vals)),'nonzero_fraction':sum(v!=0 for v in vals)/max(1,len(vals)),'status':'descriptive_activation_not_predictive_validation'})
    csv(OUT/'feature_registry.csv',reg)
    products=[]
    from collections import defaultdict
    totals=defaultdict(float)
    for b in branches:
        for e in b['crop_events']: totals[(e['mode'],e['player'],e['crop'],e['event'])]+=e['units']
    for k,v in sorted(totals.items()): products.append(dict(zip(('mode','player','crop','event'),k))|{'units':v})
    csv(OUT/'crop_event_summary.csv',products)
    own=streams['control']['key']['seat']
    report={'status':'MAINTENANCE_DIAGNOSIS_COMPLETE','decision':'DIAGNOSIS_ONLY_NO_POLICY_PROMOTION',
      'utc':utc(),'fingerprint':fp,'code_sha256':code_hash(BASE),'tests':tests,
      'source_commit':COMMIT,'engine_sha256':ENGINE,'source_episodes':1,'independent_seed_blocks':1,
      'verified_recorded_branches':2,'new_recorded_replay_transitions':new_transitions,
      'represented_recorded_transitions':1438,'reconstructed_observations':478,'plant_feature_rows':len(rows),
      'plant_descriptors':len(FIELDS),'state_descriptors':8,'mechanics_scenarios':mechanics['component_scenarios'],
      'cash_control':branches[0]['rewards'][own],'cash_defer':branches[1]['rewards'][own],
      'cash_delta_reconciled':branches[1]['rewards'][own]-branches[0]['rewards'][own],
      'all_turn_cash_and_final_state_checks_passed':True,'cash_decomposition':dec,
      'feature_extractor_max_ms':max(x for b in branches for x in b['feature_latency_ms']),
      'new_policy_calls':0,'new_interventions':0,'models_fit':0,'official_submission_score':None,
      'official_metric_improvement_measured':False,'feature_value_proven':False,'full_callback_acceptance':'NOT_RUN',
      'github_updated':False,'cloud_resources_modified':False,'elapsed_seconds':time.monotonic()-start,
      'limitations':['One previously selected development source, no independent validation.',
      'Recorded actions reconstruct the rejected trajectories; no retries of the policy experiment.',
      'Trade price/quantity decomposition is an accounting identity, not an independent causal effect.',
      'Crop scenario pathways omit travel, future fertilizer and joint worker constraints; no scenario is promoted to a policy.',
      'Feature rows and post-outcome diagnostic rows remain separate; no learned selector was fitted.',
      'Complete-agent workforce restriction is not changed.'],
      'output_sha256':{n:sha(OUT/n) for n in ('cash_decomposition.csv','crop_event_summary.csv','crop_features.csv.gz','state_features.csv','trades.csv.gz','crop_events.csv.gz','cash.csv','feature_registry.csv','mechanics.json')}}
    write(OUT/'report.json',report); log(report['status'],cash_delta=report['cash_delta_reconciled'])

def verify_completed():
    r=read(OUT/'report.json'); s=read(OUT/'status.json')
    if s.get('status')!='COMPLETED' or s.get('report_sha256')!=sha(OUT/'report.json') or r['code_sha256']!=code_hash(BASE): raise ValueError('Completed result identity differs')
    for n,h in r['output_sha256'].items():
        if sha(inside(OUT,n))!=h: raise ValueError('Completed output differs: '+n)
    return r

def supervise(home):
    path=OUT/'status.json'; OUT.mkdir(exist_ok=True)
    if path.exists():
        if read(path).get('status')=='COMPLETED':
            verify_package(); verify_completed()
            from review_inputs import action_stream
            action_stream(home/'kaggriculture_water_maintenance',read(BASE/'reference/input_hashes.json'))
            log('VERIFIED_DIAGNOSIS_REUSED'); return
        raise RuntimeError('Earlier run failed, active or interrupted. Bundle diagnostics; no unchanged retry.')
    with path.open('x') as f: json.dump({'status':'RUNNING','utc':utc()},f)
    child=None
    old_term=signal.getsignal(signal.SIGTERM)
    def terminated(signum, frame):
        raise KeyboardInterrupt('Supervisor terminated')
    signal.signal(signal.SIGTERM, terminated)
    try:
        child=subprocess.Popen([sys.executable,str(BASE/'run_diagnosis.py'),'_worker','--home',str(home)],start_new_session=True)
        start=last=time.monotonic()
        while child.poll() is None:
            now=time.monotonic()
            if now-start>CAP: raise TimeoutError('120-second diagnostic cap reached')
            if now-last>=10: log('HEARTBEAT',elapsed_seconds=round(now-start,1)); last=now
            time.sleep(.2)
        if child.returncode: raise RuntimeError('Diagnosis stopped; preserve diagnostics')
        write(path,{'status':'COMPLETED','utc':utc(),'report_sha256':sha(OUT/'report.json')})
    except BaseException as e:
        if child and child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try: child.wait(timeout=2)
            except subprocess.TimeoutExpired: os.killpg(child.pid,signal.SIGKILL); child.wait()
        write(path,{'status':'FAILED','utc':utc(),'error':str(e)})
        raise
    finally:
        signal.signal(signal.SIGTERM, old_term)

def bundle():
    # Allowlisted generated paths: never include raw episodes, environments or credentials.
    target=BASE/'kaggriculture_maintenance_diagnosis_results.zip'
    paths=sorted(p for p in OUT.rglob('*') if p.is_file() and not p.is_symlink() and p.suffix in ('.json','.jsonl','.txt','.csv','.gz','.html')) if OUT.exists() else []
    paths += [BASE/'13_maintenance_loss_and_interaction_features.ipynb',BASE/'PROTOCOL.json',BASE/'LOCAL_VALIDATION.json']
    paths=[p for p in paths if p.exists()]
    manifest={'utc':utc(),'files':{str(p.relative_to(BASE)):sha(p) for p in paths}}
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in paths: z.write(p,str(p.relative_to(BASE)))
        z.writestr('BUNDLE_MANIFEST.json',json.dumps(manifest,indent=2))
    print(str(target))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('command',choices=['run','_worker','bundle']); ap.add_argument('--home',type=Path,default=Path.home()); args=ap.parse_args()
    if args.command=='bundle': bundle(); return
    if args.command=='run': supervise(args.home); return
    try: worker(args.home)
    except BaseException:
        write(OUT/'failure.json',{'utc':utc(),'traceback':traceback.format_exc()}); raise
if __name__=='__main__': main()
