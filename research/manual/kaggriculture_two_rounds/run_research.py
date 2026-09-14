"""Bounded manual research. No remote writes, installs, automatic retries or submissions."""
from __future__ import annotations
import argparse,importlib,gzip,json,os,re,signal,subprocess,sys,tempfile,time,traceback,unittest,zipfile
from pathlib import Path
from copy import deepcopy
from io_utils import atomic,code_hash,digest,inside,load,read,save,sha,utc,write
BASE=Path(__file__).resolve().parent;OUT=BASE/'outputs'

def log(event,**data):
    OUT.mkdir(exist_ok=True);r={'utc':utc(),'event':event,**data}
    with (OUT/'events.jsonl').open('a') as f:f.write(json.dumps(r,allow_nan=False)+'\n');f.flush()
    print(json.dumps(r,allow_nan=False),flush=True)
def emit(event,row):
    write(OUT/'latest_measurement.json',{'event':event,**row})
    with (OUT/'callback_trace.jsonl').open('a') as f:f.write(json.dumps({'utc':utc(),'event':event,**row},allow_nan=False)+'\n');f.flush()
def csv(path,rows):
    import pandas as pd
    data=pd.DataFrame(rows).to_csv(index=False).encode();atomic(path,gzip.compress(data,mtime=0) if str(path).endswith('.gz') else data)
def verify_package():
    m=read(BASE/'PACKAGE_MANIFEST.json')
    for n,h in m['files'].items():
        if sha(inside(BASE,n))!=h:raise ValueError('Package changed: '+n)
    for n,h in m['notebooks'].items():
        nb=read(BASE/n);body=[{'cell_type':c['cell_type'],'source':''.join(c['source']) if isinstance(c['source'],list) else c['source']} for c in nb['cells']]
        if digest(body)!=h:raise ValueError('Notebook source changed; saved outputs are allowed')
def test_stage(rid):
    start=time.monotonic();suite=unittest.TestSuite()
    loader=unittest.defaultTestLoader
    for pattern in ['test_common.py',f'test_round{rid}.py']:
        suite.addTests(loader.discover(str(BASE/'tests'),pattern=pattern,top_level_dir=str(BASE)))
    result=unittest.TextTestRunner(verbosity=1,stream=sys.stdout).run(suite)
    report={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'seconds':time.monotonic()-start}
    write(OUT/f'round{rid}'/'tests.json',report)
    if not result.wasSuccessful() or result.skipped:raise RuntimeError('Tests failed or skipped')
    return report

def preflight(home):
    verify_package();protocol=read(BASE/'PROTOCOL.json');old=home/'kaggriculture_manual_resume';prior=home/'kaggriculture_renewal_factorial'
    for n,h in read(BASE/'reference/input_review.json')['prior_result_hashes'].items():
        if sha(inside(prior,n))!=h:raise ValueError('Prior notebook16 evidence changed: '+n)
    source=read(old/'state/source.json');runtime=read(old/'state/runtime.json');ready=read(old/'state/readiness.json');restore=read(old/'state/restore.json')
    if any(r.get('status')!='PASSED' for r in (source,runtime,restore)):raise ValueError('Incomplete prior readiness')
    if sys.version_info[:2]!=(3,12) or Path(sys.executable).absolute()!=Path(runtime['executable']).absolute():raise ValueError('Use Kaggriculture Manual (verified source), not a new installation')
    repo=Path(source['repo']).resolve()
    def git(*args):return subprocess.check_output(['git',*args],cwd=repo,text=True,timeout=10).strip()
    if git('rev-parse','HEAD')!=protocol['source_commit'] or git('status','--porcelain','--untracked-files=no'):raise ValueError('Reviewed repository changed; preserve it, do not reset')
    for n,h in ready['source_files'].items():
        if sha(inside(repo,n))!=h:raise ValueError('Source receipt mismatch')
    sys.path.insert(0,str(repo/'src'));sys.path.insert(0,str(BASE/'baseline'))
    from kaggriculture_research import environment
    if not Path(environment.__file__).resolve().is_relative_to(repo/'src'):raise ValueError('Wrong repository import')
    manifest=environment.engine_manifest()
    if manifest['files']['envs/kaggriculture/kaggriculture.py']!=protocol['engine_sha256']:raise ValueError('Engine changed')
    for name in ('callback','cash_features','timing_features'):
        module=importlib.import_module(name)
        if Path(module.__file__).resolve()!=BASE/'baseline'/f'{name}.py':raise ValueError('Wrong baseline import')
    root=Path(restore['private_root']).resolve()
    if restore['episode_count']!=7 or len(restore['downloaded_or_reused'])!=10:raise ValueError('Incomplete restored artifacts')
    for item in restore['downloaded_or_reused']:
        p=inside(root,item['path'])
        if p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:raise ValueError('Restored object changed')
    progress=read(root/'reports/staffing_progress.json')
    if manifest!=progress['lineage']['engine']:raise ValueError('Full recorded engine manifest differs')
    seeds={b['seed'] for b in protocol['paired_blocks']};hits=[];scanned=0
    # Inventory repository code/config/docs/test seeds and known manual evidence. Do not scan environments or data archives.
    for folder in ('configs','tests','scripts','src','docs','reports'):
        for p in (repo/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.py','.json','.md','.csv') and p.stat().st_size<2_000_000:
                text=p.read_text(errors='replace');scanned+=1
                for seed in seeds:
                    if re.search(r'(?<!\d)'+str(seed)+r'(?!\d)',text):hits.append(str(p.relative_to(repo)))
    if any(j['seed'] in seeds for j in progress['artifact_manifest']):hits.append('restored artifact seeds')
    if hits:raise ValueError('Planned fresh seed already present; do not silently substitute: '+str(hits))
    seed_audit={'proposed_seeds':sorted(seeds),'repository_text_files_scanned':scanned,'collisions':hits,
      'known_prior_manual_seed_groups':[1601,1602],'scope':'repository textual inventory plus restored/returned known evidence; cannot certify unrecorded activity'}
    write(OUT/'seed_inventory.json',seed_audit)
    source_tree={str(p.relative_to(repo)):sha(p) for p in sorted((repo/'src').rglob('*.py'))}
    fp=digest({'code':code_hash(BASE),'protocol':protocol,'engine_manifest':manifest,'source_tree':source_tree,'restored':progress['artifact_manifest']})
    write(OUT/'preflight.json',{'status':'PASSED','utc':utc(),'fingerprint':fp,'source_commit':protocol['source_commit'],'engine':manifest,
      'verified_objects':10,'prior_result_verified':True,'seed_inventory':seed_audit,'new_cloud_resources':0})
    log('PREFLIGHT_PASSED',verified_objects=10,proposed_fresh_development_seeds=sorted(seeds))
    return environment,root,progress,fp

def common(fp,rid):return {'utc':utc(),'fingerprint':fp,'code_sha256':code_hash(BASE),'round':rid,'official_submission_score':None,'official_metric_effect_measured':False,'models_fit':0,'github_updated':False,'cloud_resources_modified':False,'feature_engineering_complete':False,'validation_or_holdout_used':False}

def screen(rid,home):
    started=time.monotonic();tests=test_stage(rid);env,root,progress,fp=preflight(home)
    from mechanics import validate
    from policies import FeaturePolicy
    from experiment import measure
    from kaggriculture_research.artifacts import load_checkpoint
    from kaggriculture_staffing.experiment import validate_episode
    module=importlib.import_module('arrival_features' if rid=='17' else 'headroom_features')
    folder=OUT/f'round{rid}'/'screen';folder.mkdir(parents=True,exist_ok=True)
    checks=validate(env.game,rid);write(folder/'mechanics.json',checks);log('MECHANICS_PASSED',round=rid,cases=checks['cases'])
    rows=[];tasks=[];protocol=read(BASE/'PROTOCOL.json');wanted=set(protocol['screen_steps'])
    jobs=sorted((j for j in progress['artifact_manifest'] if j['arm']=='coordinated'),key=lambda j:(j['seed'],j['seat']))
    if len(jobs)!=3:raise ValueError('Expected three coordinated screening sources')
    for idx,j in enumerate(jobs):
        key={k:j[k] for k in ('seed','seat','opponent','arm')};cache=folder/'checkpoints'/f'source{idx}.json.gz';cf=digest({'fp':fp,'round':rid,'source':j['sha256']})
        data=load(cache,cf)
        if data is None:
            p=load_checkpoint(inside(root,j['path']),{**progress['lineage'],**key})
            if p is None:raise ValueError('Restored checkpoint lineage mismatch')
            validate_episode(p,key);rr=[];tt=[]
            for rec in p['records']:
                obs=rec['observation']
                if rec['player']!=key['seat'] or obs['step'] not in wanted:continue
                actor=FeaturePolicy(env.game,rid,'candidate');control=FeaturePolicy(env.game,rid,'control');null=FeaturePolicy(env.game,rid,'null')
                for a in (actor,control,null):a.prime(obs['step']-1,obs['player'])
                a,ms=measure(actor,obs,'screen_candidate',emit);ref,rms=measure(control,obs,'screen_control',emit);shadow,_=measure(null,obs,'screen_null',emit)
                if ref!=shadow or ref!=rec['action']:raise ValueError('Archived/null control-action mismatch')
                tr,sv=module.extract(obs,env.game)
                rr.append({**key,'step':obs['step'],'day':obs['day'],'changed':int(a!=ref),'candidate_ms':ms,'reference_ms':rms,**sv})
                tt.extend([{**key,'step':obs['step'],**r} for r in tr])
            if len(rr)!=len(wanted):raise ValueError('Missing screening observations')
            data={'states':rr,'tasks':tt};save(cache,cf,data);log('SCREEN_SOURCE_SAVED',round=rid,completed=idx+1,total=3)
        else:log('SCREEN_SOURCE_REUSED',round=rid,source=idx+1)
        rows.extend(data['states']);tasks.extend(data['tasks'])
    csv(folder/'states.csv',rows);csv(folder/'task_features.csv.gz',tasks)
    registry=[]
    for n in module.FIELDS:
        v=[r[n] for r in tasks];registry.append({'feature':n,'distinct_values':len(set(v)),'nonzero_fraction':sum(x!=0 for x in v)/max(1,len(v)),'status':'candidate_activation_not_importance'})
    csv(folder/'feature_registry.csv',registry)
    changes=sum(r['changed'] for r in rows)
    report={**common(fp,rid),'status':'FEATURE_SCREEN_COMPLETE','tests':tests,'observations':len(rows),'task_rows':len(tasks),
      'task_descriptors':32,'state_descriptors':12,'action_changes':changes,'candidate_callback_max_ms':max(r['candidate_ms'] for r in rows),
      'decision':'FRESH_BLOCKS_ALLOWED' if changes else 'STOP_NO_ACTION_ACTIVATION','new_games':0,'elapsed_seconds':time.monotonic()-started,
      'output_sha256':{n:sha(folder/n) for n in ['states.csv','task_features.csv.gz','feature_registry.csv','mechanics.json']}}
    write(folder/'report.json',report);log('FEATURE_SCREEN_COMPLETE',round=rid,decision=report['decision'],changes=changes)

def verify_stage(rid,stage):
    folder=OUT/f'round{rid}'/stage;s=read(folder/'status.json');r=read(folder/'report.json')
    if s.get('status')!='COMPLETED' or s['report_sha256']!=sha(folder/'report.json') or r['code_sha256']!=code_hash(BASE):raise ValueError('Stage integrity mismatch')
    for n,h in r.get('output_sha256',{}).items():
        if sha(inside(folder,n))!=h:raise ValueError('Stage artifact changed')
    if 'shared_control_sha256' in r:
        if sha(OUT/'shared_controls'/f'{r["block"]["id"]}.json.gz')!=r['shared_control_sha256']:raise ValueError('Shared control changed')
    return r

def pair(rid,number,home):
    started=time.monotonic();env,root,progress,fp=preflight(home);sr=verify_stage(rid,'screen')
    if sr['fingerprint']!=fp:raise ValueError('Screen lineage changed')
    folder=OUT/f'round{rid}'/f'pair{number}';folder.mkdir(parents=True,exist_ok=True)
    blocked=sr['decision']=='STOP_NO_ACTION_ACTIVATION';reason='STOP_NO_ACTION_ACTIVATION'
    for n in range(1,number):
        prev=verify_stage(rid,f'pair{n}')
        if prev['decision'] in ('STOP_NEGATIVE_ENDPOINT','SKIPPED_PREVIOUS_STOP'):
            blocked=True;reason='SKIPPED_PREVIOUS_STOP'
    if blocked:
        r={**common(fp,rid),'status':'PAIR_SKIPPED','decision':reason,'new_games':0,'output_sha256':{}}
        write(folder/'report.json',r);log('PAIR_SKIPPED',round=rid,block=number,reason=reason);return
    from experiment import run_game,compare
    block=read(BASE/'PROTOCOL.json')['paired_blocks'][number-1];branches={};new_count=0
    for mode in ('control','candidate'):
        cache=(OUT/'shared_controls'/f'{block["id"]}.json.gz') if mode=='control' else folder/'candidate.json.gz'
        identity=digest({'experiment':fp,'block':block,'mode':'shared_control' if mode=='control' else rid})
        branch=load(cache,identity)
        if branch is None:
            branch=run_game(env.game,env.make_environment,rid,mode,block,emit,log)
            if mode=='control':branch['round']='shared'
            save(cache,identity,branch);new_count+=1;log('GAME_CHECKPOINT_SAVED',round=rid,block=number,mode=mode,coins=branch['metrics']['coins'])
        else:log('GAME_CHECKPOINT_REUSED',round=rid,block=number,mode=mode)
        branches[mode]=branch
    result=compare(branches['control'],branches['candidate']);csv(folder/'comparison.csv',[result])
    states=[];features=[];traces=[]
    for mode,b in branches.items():
        for r in b['states'][rid]:states.append({'mode':mode,**r})
        for r in b['features'][rid]:features.append({'mode':mode,**r})
        for r in b['trace']:traces.append({'mode':mode,**{k:v for k,v in r.items() if k not in ('action','reference_action','opponent_action','observed_market','own_crop_counts_after')}})
    csv(folder/'states.csv',states);csv(folder/'task_features.csv.gz',features);csv(folder/'trajectories.csv',traces)
    report={**common(fp,rid),'status':'PAIRED_BLOCK_COMPLETE','block':block,'decision':result['decision'],'comparison':result,
      'new_games':new_count,'represented_games':2,'control_reused':new_count<2,'elapsed_seconds':time.monotonic()-started,
      'candidate_callback_max_ms':branches['candidate']['candidate_callback_max_ms'],
      'all_actors_callback_max_ms':max(b['callback_max_ms'] for b in branches.values()),
      'shared_control_sha256':sha(OUT/'shared_controls'/f'{block["id"]}.json.gz'),
      'output_sha256':{n:sha(folder/n) for n in ['comparison.csv','states.csv','task_features.csv.gz','trajectories.csv','candidate.json.gz']}}
    write(folder/'report.json',report);log('PAIRED_BLOCK_COMPLETE',round=rid,block=number,decision=result['decision'],coins_delta=result['coins_delta'],margin_delta=result['coin_margin_delta'])

def summary(rid):
    import pandas as pd
    reports=[verify_stage(rid,f'pair{i}') for i in range(1,5)];completed=[r for r in reports if 'comparison' in r]
    rows=[r['comparison'] for r in completed];csv(OUT/f'round{rid}'/'comparisons.csv',rows)
    r={'status':'ROUND_COMPLETE','round':rid,'completed_pairs':len(completed),'planned_pairs':4,'development_seed_groups':len({r['block']['seed'] for r in completed}),
       'opponents_tested':sorted({r['block']['opponent'] for r in completed}),'seats_tested':sorted({r['block']['seat'] for r in completed}),
       'automatic_promotion':False,'official_submission_score':None,'official_metric_effect_measured':False,
       'decision':'REVIEW_FRESH_DEVELOPMENT_BLOCKS_NO_PROMOTION','limitations':['Only two new development seeds; not an untouched final holdout.','Four balanced, not fully crossed seed/opponent/seat blocks; no isolated factor effects.','Shared controls make comparisons across rounds correlated.','Crop and livestock references are source-distinct, not established leaderboard-strength opponents.','Three-hired-hand callback restriction unchanged.','No fitted weights, feature selection, or significance claim.','Stopped blocks are missing, not zero effects.'],
       'comparisons':rows}
    write(OUT/f'round{rid}'/'summary.json',r);log('ROUND_COMPLETE',round=rid,completed_pairs=len(completed),planned_pairs=4)

def kill_group(child):
    if child and child.poll() is None:
        os.killpg(child.pid,signal.SIGTERM)
        try:child.wait(timeout=2)
        except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()

def supervise(rid,stage,home):
    path=OUT/f'round{rid}'/stage/'status.json'
    if path.exists():
        if read(path).get('status')=='COMPLETED':
            r=verify_stage(rid,stage);*_,fp=preflight(home)
            if fp!=r['fingerprint']:raise ValueError('Current lineage differs')
            log('STAGE_REUSED',round=rid,stage=stage);return
        raise RuntimeError('Earlier attempt failed/active/interrupted. Bundle it; no unchanged retry.')
    path.parent.mkdir(parents=True,exist_ok=True)
    lock=OUT/'.execution.lock'
    try:
        with lock.open('x') as f:json.dump({'pid':os.getpid(),'round':rid,'stage':stage},f)
    except FileExistsError:
        raise RuntimeError('Another stage is running or interrupted. Do not run notebooks in parallel; preserve the lock and bundle diagnostics.')
    with path.open('x') as f:json.dump({'status':'RUNNING','utc':utc()},f)
    child=None;old=signal.getsignal(signal.SIGTERM)
    def interrupted(s,f):raise KeyboardInterrupt('Supervisor terminated')
    signal.signal(signal.SIGTERM,interrupted)
    try:
        child=subprocess.Popen([sys.executable,str(BASE/'run_research.py'),'_worker','--round',rid,'--stage',stage,'--home',str(home)],start_new_session=True)
        start=last=time.monotonic();cap=120 if stage=='screen' else 180
        while child.poll() is None:
            now=time.monotonic()
            if now-start>cap:raise TimeoutError(f'{cap}-second stage cap')
            if now-last>=10:log('HEARTBEAT',round=rid,stage=stage,elapsed_seconds=round(now-start,1));last=now
            time.sleep(.2)
        if child.returncode:raise RuntimeError('Worker failed; preserve diagnostics')
        report=path.parent/'report.json';write(path,{'status':'COMPLETED','utc':utc(),'report_sha256':sha(report)})
    except BaseException as e:
        kill_group(child);write(path,{'status':'FAILED','utc':utc(),'error':str(e)});raise
    finally:
        signal.signal(signal.SIGTERM,old)
        if lock.exists() and read(lock).get('pid')==os.getpid():lock.unlink()

def bundle():
    paths=[p for p in OUT.rglob('*') if p.is_file() and not p.is_symlink() and p.suffix in ('.json','.jsonl','.csv','.gz','.txt','.html')]
    paths += [p for p in BASE.glob('*.ipynb')]+[BASE/'PROTOCOL.json',BASE/'LOCAL_VALIDATION.json',BASE/'reference/input_review.json']
    paths=[p for p in paths if p.exists()]
    if sum(p.stat().st_size for p in paths)>250_000_000:raise ValueError('Unexpected bundle size; inspect before exporting')
    manifest={'utc':utc(),'files':{str(p.relative_to(BASE)):sha(p) for p in paths}}
    dest=BASE/'kaggriculture_two_rounds_results.zip';fd,tmp=tempfile.mkstemp(prefix='.bundle-',dir=BASE);os.close(fd)
    try:
        with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
            for p in paths:z.write(p,str(p.relative_to(BASE)))
            z.writestr('BUNDLE_MANIFEST.json',json.dumps(manifest,indent=2))
        os.replace(tmp,dest)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    print('RESULTS_BUNDLE:',dest)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['screen','pair','summary','tests','bundle','_worker']);ap.add_argument('--round',choices=['17','18'],default='17');ap.add_argument('--block',type=int,choices=range(1,5),default=1);ap.add_argument('--stage');ap.add_argument('--home',type=Path,default=Path.home());a=ap.parse_args()
    try:
        if a.command=='bundle':bundle()
        elif a.command=='tests':test_stage(a.round)
        elif a.command=='summary':summary(a.round)
        elif a.command=='_worker':
            if a.stage=='screen':screen(a.round,a.home)
            elif a.stage in ['pair1','pair2','pair3','pair4']:pair(a.round,int(a.stage[-1]),a.home)
            else:raise ValueError('Unknown worker stage')
        else:supervise(a.round,'screen' if a.command=='screen' else f'pair{a.block}',a.home)
    except BaseException:
        write(OUT/f'round{a.round}'/f'failure_{a.command}_{a.stage or a.block}.json',{'utc':utc(),'traceback':traceback.format_exc()});raise
if __name__=='__main__':main()
