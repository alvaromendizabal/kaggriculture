"""Two bounded stages, local artifacts only; no installation, cloud or Git writes."""
from __future__ import annotations
import argparse
from copy import deepcopy
import gzip
import importlib
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
from factorial_io import atomic, code_hash, digest, inside, load_cache, read, save_cache, sha, utc, write

BASE=Path(__file__).resolve().parent
OUT=BASE/'outputs'
COMMIT='7194116dfc92a8663139611233b5a221dad431a4'
ENGINE='bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e'
CAPS={'screen':120,'pilot':120}


def log(stage,**kwargs):
    OUT.mkdir(exist_ok=True)
    row={'utc':utc(),'stage':stage,**kwargs}
    with (OUT/'events.jsonl').open('a') as f: f.write(json.dumps(row,allow_nan=False)+'\n');f.flush()
    print(json.dumps(row,allow_nan=False),flush=True)


def emit(event,row):
    write(OUT/'latest_measurement.json',{'event':event,**row})
    with (OUT/'callback_trace.jsonl').open('a') as f:f.write(json.dumps({'utc':utc(),'event':event,**row},allow_nan=False)+'\n');f.flush()


def save_csv(path,rows,columns=None):
    import pandas as pd
    data=pd.DataFrame(rows,columns=columns).to_csv(index=False).encode()
    atomic(path,gzip.compress(data,mtime=0) if str(path).endswith('.gz') else data)


def verify_package():
    manifest=read(BASE/'PACKAGE_MANIFEST.json')
    for name,h in manifest['files'].items():
        if sha(inside(BASE,name))!=h: raise ValueError('Package file changed: '+name)
    nb=read(BASE/'16_renewal_factorial_feature_ablation.ipynb')
    body=[{'cell_type':c['cell_type'],'source':''.join(c['source']) if isinstance(c['source'],list) else c['source']} for c in nb['cells']]
    if digest(body)!=manifest['notebook_source_sha256']:raise ValueError('Notebook source changed; saved outputs are allowed')


def test_stage():
    result=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(unittest.defaultTestLoader.discover(str(BASE/'tests')))
    r={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)}
    write(OUT/'tests.json',r)
    if not result.wasSuccessful() or result.skipped: raise RuntimeError('Tests failed/skipped')
    return r


def preflight(home):
    verify_package()
    from factorial_analysis import historical_branches
    previous=home/'kaggriculture_crop_lifecycle'
    branches,prior=historical_branches(previous,read(BASE/'reference/input_hashes.json'))
    if code_hash(previous)!=prior['code_sha256']:raise ValueError('Notebook15 source changed; preserve it')
    protocol=read(BASE/'PROTOCOL.json');key=protocol['source_key']
    if key!=prior['selected_key']:raise ValueError('Do not switch source blocks')
    old=home/'kaggriculture_manual_resume'
    source=read(old/'state/source.json');runtime=read(old/'state/runtime.json')
    restore=read(old/'state/restore.json');ready=read(old/'state/readiness.json')
    if any(r.get('status')!='PASSED' for r in (source,runtime,restore)):raise ValueError('Readiness incomplete')
    if sys.version_info[:2]!=(3,12) or Path(sys.executable).absolute()!=Path(runtime['executable']).absolute():
        raise ValueError('Select Kaggriculture Manual (verified source); do not reinstall')
    repo=Path(source['repo']).resolve()
    def git(*args):return subprocess.check_output(['git',*args],cwd=repo,text=True,timeout=10).strip()
    if git('rev-parse','HEAD')!=COMMIT or git('status','--porcelain','--untracked-files=no'):
        raise ValueError('Reviewed checkout changed; do not reset')
    for name,h in ready['source_files'].items():
        if sha(inside(repo,name))!=h:raise ValueError('Reviewed source hash mismatch')
    for folder,entries in read(BASE/'reference/dependency_hashes.json').items():
        for name,h in entries.items():
            if sha(inside(home/folder,name))!=h:raise ValueError('Dependency changed: '+folder+'/'+name)
    sys.path.insert(0,str(repo/'src'))
    from kaggriculture_research import environment
    if not Path(environment.__file__).resolve().is_relative_to(repo/'src'):raise ValueError('Wrong environment import')
    if environment.engine_manifest()['files']['envs/kaggriculture/kaggriculture.py']!=ENGINE:raise ValueError('Pinned engine changed')
    for folder,names in [('kaggriculture_cash_realization',('cash_features','callback')),('kaggriculture_sale_timing',('timing_features',))]:
        sys.path.insert(0,str(home/folder))
        for name in names:
            module=importlib.import_module(name)
            if Path(module.__file__).resolve()!=(home/folder/(name+'.py')).resolve():raise ValueError('Wrong dependency module: '+name)
    root=Path(restore['private_root']).resolve()
    if restore['episode_count']!=7 or len(restore['downloaded_or_reused'])!=10:raise ValueError('Recovery scope mismatch')
    for obj in restore['downloaded_or_reused']:
        p=inside(root,obj['path'])
        if p.stat().st_size!=obj['bytes'] or sha(p)!=obj['sha256']:raise ValueError('Recovered object differs')
    progress=read(root/'reports/staffing_progress.json')
    if environment.engine_manifest()!=progress['lineage']['engine']:raise ValueError('Recorded framework/engine manifest differs')
    jobs=[j for j in progress['artifact_manifest'] if all(j[k]==v for k,v in key.items())]
    if len(jobs)!=1:raise ValueError('Source key not unique')
    job=jobs[0]
    from kaggriculture_research.artifacts import load_checkpoint
    from kaggriculture_staffing.experiment import validate_episode
    payload=load_checkpoint(inside(root,job['path']),{**progress['lineage'],**key})
    if payload is None or sha(inside(root,job['path']))!=job['sha256']:raise ValueError('Raw source lineage mismatch')
    validate_episode(payload,key)
    fp=digest({'code':code_hash(BASE),'protocol':sha(BASE/'PROTOCOL.json'),'engine':ENGINE,'source':job['sha256'],
      'previous':sha(previous/'outputs/pilot/report.json'),'dependency_manifest':sha(BASE/'reference/dependency_hashes.json')})
    write(OUT/'preflight.json',{'status':'PASSED','utc':utc(),'fingerprint':fp,'source_commit':COMMIT,'engine_sha256':ENGINE,
      'source_key':key,'verified_objects':10,'reused_prior_branches':3})
    log('PREFLIGHT_PASSED',verified_objects=10,reused_prior_branches=3)
    return payload,branches,environment,fp,key


def common(fp):
    return {'utc':utc(),'fingerprint':fp,'code_sha256':code_hash(BASE),'source_commit':COMMIT,'engine_sha256':ENGINE,
      'github_updated':False,'cloud_resources_modified':False,'models_fit':0,'official_submission_score':None,
      'official_metric_effect_measured':False,'feature_engineering_complete':False,'validation_or_holdout_used':False}


def screen(home):
    start=time.monotonic();tests=test_stage()
    payload,old,environment,fp,key=preflight(home)
    from mechanics import validate
    checks=validate(environment.game)
    write(OUT/'mechanics.json',checks);log('MECHANICS_PASSED',calendar_cases=checks['calendar_cases'],dig_replant_cases=checks['dig_replant_cases'])
    from factorial_experiment import screen_block
    from kaggriculture_terminal.feed_policy import CROP_LAYOUT
    from joint_features import FIELDS
    rows=[]
    for day in range(8,30):
        path=OUT/'screen/checkpoints'/f'day{day:02d}.json.gz'
        cpf=digest({'run':fp,'day':day})
        cached=load_cache(path,cpf)
        if cached is None:
            cached=screen_block(payload,key,old['control'],environment.game,CROP_LAYOUT,day*24,min(718,day*24+23),emit)
            save_cache(path,cpf,cached);log('SCREEN_DAY_SAVED',day=day,states=len(cached))
        else:log('SCREEN_DAY_REUSED',day=day)
        rows.extend(cached)
    if len(rows)!=527 or [r['step'] for r in rows]!=list(range(192,719)):raise ValueError('Incomplete full-path screen')
    save_csv(OUT/'screen/states.csv',rows)
    full_path=OUT/'screen/full_path.json.gz'
    if full_path.exists():
        if load_cache(full_path,fp)!=rows:raise ValueError('Full-path checkpoint differs from daily checkpoints')
    else:save_cache(full_path,fp,rows)
    registry=[{'feature':f,'distinct_values':len({r[f] for r in rows}),'nonzero_fraction':sum(r[f]!=0 for r in rows)/len(rows),
       'status':'logged_candidate_not_action_weight_or_importance'} for f in FIELDS]
    save_csv(OUT/'screen/feature_registry.csv',registry)
    changes=sum(r['changed'] for r in rows)
    report={**common(fp),'status':'RENEWAL_FACTORIAL_SCREEN_COMPLETE','tests':tests,'decision':'RUN_ONE_CLEAR_ONLY_BRANCH' if changes else 'CERTIFY_IDENTITY_REUSE_CONTROL',
      'observations':len(rows),'action_changes':changes,'null_parity_checks':len(rows),'archived_action_checks':len(rows),
      'state_descriptors':len(FIELDS),'new_interpreter_transitions':0,'candidate_callback_max_ms':max(r['candidate_callback_ms'] for r in rows),
      'elapsed_seconds':time.monotonic()-start,'source_key':key,
      'output_sha256':{n:sha(OUT/n) for n in ('mechanics.json','screen/states.csv','screen/feature_registry.csv','screen/full_path.json.gz')}}
    write(OUT/'screen/report.json',report);log(report['status'],decision=report['decision'],action_changes=changes)


def verify_stage(stage):
    r=read(OUT/stage/'report.json');s=read(OUT/stage/'status.json')
    if s.get('status')!='COMPLETED' or s.get('report_sha256')!=sha(OUT/stage/'report.json') or r['code_sha256']!=code_hash(BASE):
        raise ValueError('Completed stage integrity changed')
    for n,h in r['output_sha256'].items():
        if sha(inside(OUT,n))!=h:raise ValueError('Completed artifact changed: '+n)
    return r


def pilot(home):
    start=time.monotonic();payload,branches,environment,fp,key=preflight(home)
    screened=verify_stage('screen')
    if screened['fingerprint']!=fp:raise ValueError('Screen lineage changed')
    from factorial_analysis import assess,full_factorial,MODES,BITS
    from factorial_experiment import identical_branch,rollout
    from kaggriculture_terminal.feed_policy import CROP_LAYOUT
    path=OUT/'pilot/checkpoints/clear_only.json.gz'
    cpf=digest({'run':fp,'mode':'clear_only'})
    new=load_cache(path,cpf);new_count=0
    if new is None:
        if screened['action_changes']==0:
            new=identical_branch(branches['control'],load_cache(OUT/'screen/full_path.json.gz',fp))
        else:
            new=rollout(payload,key,branches['control'],environment.game,environment.make_environment,CROP_LAYOUT,emit,log)
            new_count=new['new_transitions']
        save_cache(path,cpf,new);log('CLEAR_ONLY_CHECKPOINT_SAVED',coins=new['metrics']['coins'],method=new['evidence_method'])
    else:log('CLEAR_ONLY_CHECKPOINT_REUSED')
    branches['clear_only']=new
    contrasts=[assess(branches['control'],branches[m]) for m in ('retire','clear_only','renew')]
    effects=full_factorial(branches)
    endpoints=[{'mode':m,'retirement':BITS[m][0],'early_clear':BITS[m][1],'evidence':'reused_notebook15' if m!='clear_only' else new['evidence_method'],**branches[m]['metrics']} for m in MODES]
    save_csv(OUT/'pilot/endpoints.csv',endpoints);save_csv(OUT/'pilot/contrasts.csv',contrasts);save_csv(OUT/'pilot/factorial_effects.csv',effects)
    trajectories=[]
    for m in MODES:
        for r in branches[m]['trace']:
            trajectories.append({k:r.get(k,0) for k in ('step','day','own_cash','opponent_cash','water_commands','dig_commands','plant_commands')}|{'mode':m})
    save_csv(OUT/'pilot/trajectories.csv',trajectories)
    # Keep current-state features separate from outcome tables.
    save_csv(OUT/'pilot/clear_only_features.csv',[{'step':r['step'],**r['features']} for r in new['trace'] if 'features' in r])
    r={**common(fp),'status':'RENEWAL_FACTORIAL_COMPLETE','decision':'FACTORIAL_DIAGNOSIS_COMPLETE_NO_AUTOMATIC_PROMOTION','source_key':key,
       'reused_prior_branches':3,'new_policy_branches':int(new['evidence_method']=='one_new_responsive_continuation'),
       'new_transitions_this_invocation':new_count,'represented_new_arm_transitions':new['new_transitions'],
       'clear_only_evidence_method':new['evidence_method'],'independent_seed_blocks':1,'arms_are_correlated':True,
       'endpoints':endpoints,'contrasts':contrasts,'factorial_effects':effects,'new_arm_decision':next(c for c in contrasts if c['contrast']=='clear_only-control'),
       'elapsed_seconds':time.monotonic()-start,'candidate_callback_max_ms':max(t['candidate_callback_ms'] for t in new['trace']),
       'limitations':['Same adaptively chosen, repeatedly examined development seed and one related opponent; no independent validation.',
         'Cash guard is preserved separately from win/margin interpretation. No post-hoc metric switch or policy promotion.',
         'Difference-in-differences is a conditional block contrast, not an independent additive causal decomposition or significance test.',
         'Historical branches were reused from checksum-verified checkpoints, not simulated again.',
         'Ordinary WATER eligibility is unchanged, but indirect WATER schedules and purchases may change after clearing.',
         'Joint descriptors are logged only. Existing <=3-hired-hands callback limit is unchanged.'],
       'output_sha256':{n:sha(OUT/n) for n in ('pilot/endpoints.csv','pilot/contrasts.csv','pilot/factorial_effects.csv','pilot/trajectories.csv','pilot/clear_only_features.csv','pilot/checkpoints/clear_only.json.gz')}}
    write(OUT/'pilot/report.json',r);log(r['status'],new_arm_decision=r['new_arm_decision'])


def supervise(stage,home):
    path=OUT/stage/'status.json'
    if path.exists():
        if read(path).get('status')=='COMPLETED':
            old=verify_stage(stage);_,_,_,current,_=preflight(home)
            if current!=old['fingerprint']:raise ValueError('Current lineage changed')
            log('VERIFIED_STAGE_REUSED',name=stage);return
        raise RuntimeError('Prior stage failed/active/interrupted: bundle diagnostics; no unchanged retry.')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump({'status':'RUNNING','utc':utc()},f)
    child=None;previous_handler=signal.getsignal(signal.SIGTERM)
    def terminate(signum,frame):raise KeyboardInterrupt('Supervisor terminated')
    signal.signal(signal.SIGTERM,terminate)
    try:
        child=subprocess.Popen([sys.executable,str(BASE/'run_factorial.py'),'_'+stage,'--home',str(home)],start_new_session=True)
        start=last=time.monotonic()
        while child.poll() is None:
            now=time.monotonic()
            if now-start>CAPS[stage]:raise TimeoutError(f'{CAPS[stage]}-second {stage} cap')
            if now-last>=10:log('HEARTBEAT',name=stage,elapsed_seconds=round(now-start,1));last=now
            time.sleep(.2)
        if child.returncode:raise RuntimeError('Stage failed; bundle diagnostics instead of retrying')
        write(path,{'status':'COMPLETED','utc':utc(),'report_sha256':sha(OUT/stage/'report.json')})
    except BaseException as e:
        if child and child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=2)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        write(path,{'status':'FAILED','utc':utc(),'error':str(e)});raise
    finally:signal.signal(signal.SIGTERM,previous_handler)


def bundle():
    paths=[p for p in OUT.rglob('*') if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(OUT.resolve()) and p.suffix in ('.json','.jsonl','.csv','.gz','.txt','.html')]
    paths += [BASE/n for n in ('16_renewal_factorial_feature_ablation.ipynb','PROTOCOL.json','FEATURE_RESEARCH.md','LOCAL_VALIDATION.json','reference/input_review.json')]
    paths=[p for p in paths if p.exists()]
    if any(p.stat().st_size>50000000 for p in paths) or sum(p.stat().st_size for p in paths)>150000000:raise ValueError('Unexpected output size')
    manifest={'utc':utc(),'files':{str(p.relative_to(BASE)):sha(p) for p in paths}}
    dest=BASE/'kaggriculture_renewal_factorial_results.zip'
    fd,tmp=tempfile.mkstemp(prefix='.bundle-',dir=BASE);os.close(fd)
    try:
        with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
            for p in paths:z.write(p,str(p.relative_to(BASE)))
            z.writestr('BUNDLE_MANIFEST.json',json.dumps(manifest,indent=2))
        os.replace(tmp,dest)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    print('RESULTS_BUNDLE:',dest,flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['screen','pilot','_screen','_pilot','tests','bundle']);ap.add_argument('--home',type=Path,default=Path.home());a=ap.parse_args()
    try:
        if a.command=='bundle':bundle()
        elif a.command=='tests':test_stage()
        elif a.command=='_screen':screen(a.home)
        elif a.command=='_pilot':pilot(a.home)
        else:supervise(a.command,a.home)
    except BaseException:
        write(OUT/('failure_'+a.command.strip('_')+'.json'),{'utc':utc(),'traceback':traceback.format_exc()});raise
if __name__=='__main__':main()
