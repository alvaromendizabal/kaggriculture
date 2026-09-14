"""Bounded notebook-10 runner: no network, installations, cloud APIs or Git writes."""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import importlib
import json
import math
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
from evidence import canonical,digest,read,sha,inside,load_branch,diagnose

BASE=Path(__file__).resolve().parent
OUT=BASE/'outputs'
COMMIT='7194116dfc92a8663139611233b5a221dad431a4'
ENGINE='bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e'
STATUS='SALE_TIMING_EXPERIMENT_COMPLETE'


def utc(): return datetime.now(timezone.utc).isoformat()
def write_bytes(p,b):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.partial-',dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f: f.write(b);f.flush();os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
def write(p,x): write_bytes(p,json.dumps(x,sort_keys=True,indent=2,allow_nan=False).encode()+b'\n')
def code_hash(root):
    return digest({str(p.relative_to(root)):sha(p) for p in sorted(Path(root).rglob('*.py')) if 'outputs' not in p.parts})
def log(stage,**kw):
    OUT.mkdir(exist_ok=True);row={'utc':utc(),'stage':stage,**kw}
    with (OUT/'events.jsonl').open('a') as f: f.write(json.dumps(row,allow_nan=False)+'\n');f.flush()
    print(json.dumps(row,allow_nan=False),flush=True)
def save_cache(p,fp,payload):
    if p.exists(): raise ValueError('Refuse checkpoint overwrite')
    x={'fingerprint':fp,'payload':payload};x['checksum']=digest(x)
    write_bytes(p,gzip.compress(canonical(x),mtime=0))
    if load_cache(p,fp)!=payload: raise ValueError('Checkpoint readback differs')
def load_cache(p,fp):
    if not p.exists():return None
    x=json.loads(gzip.decompress(p.read_bytes()));h=x.pop('checksum')
    if digest(x)!=h or x['fingerprint']!=fp:raise ValueError('Checkpoint hash/lineage differs; preserve it')
    return x['payload']

def verify_package():
    for rel,h in read(BASE/'PACKAGE_MANIFEST.json')['files'].items():
        if sha(inside(BASE,rel))!=h: raise ValueError('Package file changed: '+rel)

def verify_previous(previous,cash):
    review=read(BASE/'reference/input_review.json')
    report=previous/'outputs/report.json';r=read(report);s=read(previous/'outputs/run_status.json')
    if sha(report)!=review['report_sha256'] or s['report_sha256']!=sha(report) or s['status']!='COMPLETED':
        raise ValueError('Notebook09 current report differs; preserve it for review')
    if r['status']!='TERMINAL_CASH_EXPERIMENT_COMPLETE' or r['decision']!='STOP_NEGATIVE_TERMINAL_EFFECT':
        raise ValueError('Expected reviewed stopped experiment, not an unresolved exception')
    if code_hash(previous)!=r['code_sha256']: raise ValueError('Notebook09 source fingerprint changed')
    for rel,h in read(BASE/'reference/dependency_hashes.json')['notebook08'].items():
        if sha(inside(cash,rel))!=h: raise ValueError('Notebook08 dependency changed: '+rel)
    for rel,h in read(BASE/'reference/dependency_hashes.json')['notebook09'].items():
        if sha(inside(previous,rel))!=h: raise ValueError('Notebook09 dependency changed: '+rel)
    for rel,h in r['output_sha256'].items():
        if sha(inside(previous/'outputs',rel))!=h: raise ValueError('Notebook09 result changed: '+rel)
    cr=read(cash/'outputs/report.json');cs=read(cash/'outputs/run_status.json')
    if cr['status']!='POST_ACTION_CASH_AUDIT_PASSED' or cs['status']!='PASSED' or cs['report_sha256']!=sha(cash/'outputs/report.json'):
        raise ValueError('Notebook08 receipt is not passed')
    if cr['code_sha256']!=code_hash(cash): raise ValueError('Notebook08 source fingerprint changed')
    for rel,h in review['branch_hashes'].items():
        if sha(inside(previous/'outputs',rel))!=h:raise ValueError('Reviewed branch evidence changed')
    c=load_branch(previous/'outputs/checkpoints/c3c1b698f20aad8101da-control.json.gz')
    a=load_branch(previous/'outputs/checkpoints/c3c1b698f20aad8101da-aligned.json.gz')
    d=diagnose(c,a);write(OUT/'diagnosis.json',d);log('DIAGNOSIS_RECONCILED',cash_delta=d['cash_delta'])
    return r


def import_at(name,folder):
    sys.path.insert(0,str(folder))
    m=importlib.import_module(name)
    if Path(m.__file__).resolve()!=(folder/(name+'.py')).resolve():raise ValueError('Wrong dependency imported: '+name)
    return m


def preflight(args):
    verify_package();verify_previous(args.previous,args.cash)
    source=read(args.resume/'state/source.json');runtime=read(args.resume/'state/runtime.json')
    restored=read(args.resume/'state/restore.json');ready=read(args.resume/'state/readiness.json')
    if any(x.get('status')!='PASSED' for x in (source,runtime,restored)):
        raise ValueError('Existing source/runtime/recovery receipts not passed')
    if sys.version_info[:2]!=(3,12) or Path(sys.executable).absolute()!=Path(runtime['executable']).absolute():
        raise ValueError('Select Kaggriculture Manual (verified source); do not install a new environment')
    repo=Path(source['repo']).resolve()
    def git(*x):return subprocess.check_output(['git',*x],cwd=repo,text=True,timeout=10).strip()
    if git('rev-parse','HEAD')!=COMMIT or git('status','--porcelain','--untracked-files=no'):
        raise ValueError('Checkout changed; preserve work, do not reset')
    for rel,h in ready['source_files'].items():
        if sha(inside(repo,rel))!=h:raise ValueError('Reviewed source changed: '+rel)
    sys.path.insert(0,str(repo/'src'))
    from kaggriculture_research import environment
    if not Path(environment.__file__).resolve().is_relative_to(repo/'src'):raise ValueError('Wrong repository imports')
    if environment.engine_manifest()['files']['envs/kaggriculture/kaggriculture.py']!=ENGINE:raise ValueError('Wrong engine')
    root=Path(restored['private_root']).resolve()
    if restored['episode_count']!=7 or len(restored['downloaded_or_reused'])!=10:raise ValueError('Recovery scope changed')
    for x in restored['downloaded_or_reused']:
        p=inside(root,x['path'])
        if p.stat().st_size!=x['bytes'] or sha(p)!=x['sha256']:raise ValueError('Evidence changed: '+x['path'])
    mods={n:import_at(n,args.cash) for n in ('callback','cash_features','run_cash')}
    mods['continuation']=import_at('continuation',args.previous)
    receipt={'status':'PASSED','utc':utc(),'source_commit':COMMIT,'engine_sha256':ENGINE,
             'code_sha256':code_hash(BASE),'verified_objects':10,'repo':str(repo),'private_root':str(root)}
    write(OUT/'preflight.json',receipt);log('PREFLIGHT_PASSED',verified_objects=10)
    return root,environment.game,mods


def mechanics(game,transition):
    """Prices and expected results come from real primitives, not a fake floor.

    Compare known-demand scenarios with the actual interpreter in both seats.
    These fixtures are artificial mechanics tests, not scored research games.
    """
    from timing_features import extract,sale_path,select_action,known_demand
    from types import SimpleNamespace
    rows=[]
    for seat in (0,1):
        for product in game.PRODUCTS:
            obs={'player':seat,'step':716,'day':29,'hour':20,'farms':[game._new_farm(10,3000) for _ in (0,1)],
                 'market':game._new_market(),'town':{'unlocked_shops':['PIZZA_SHOP','PIZZA_SHOP','YARN_STORE']},
                 'private':game._new_private()}
            obs['private']['shed'][product]=4
            other=deepcopy(obs);other['player']=1-seat;other['private']=game._new_private()
            pas={'farmer':['PASS'],'hands':[],'market':[]}
            now={**deepcopy(pas),'market':[['SELL',product,4]]}
            forecast=extract(obs,obs['private'],game)
            held=transition(obs,other,pas,pas,game)
            future=[{k:deepcopy(r[k]) for k in ('player','day','hour','farms','market','town','private')} for r in held]
            for o in future:o['step']=717
            sold=transition(future[seat],future[1-seat],now,pas,game)
            cash=sold[seat]['farms'][seat]['money']-3000
            expected=forecast[f'sale_timing.{product}.h1.demand_only_value']
            if cash!=expected:raise ValueError('Known-demand/interpreter cash parity failed')
            expected_inv=obs['market']['inventory'][product]-known_demand(game,obs['town']['unlocked_shops'],product,716,1)
            if held[seat]['market']['inventory'][product]!=expected_inv:raise ValueError('Demand phase mismatch')
            rows.append({'seat':seat,'product':product,'expected':expected,'observed':cash,'kind':'known_demand','passed':True})
        # Final DROP happens before sale: compare cash, statuses and empty inventory.
        obs['step']=718;obs['hour']=22;obs['private']=game._new_private()
        obs['private']['inventories'][0]={'WHEAT':2}
        other=deepcopy(obs);other['player']=1-seat;other['private']=game._new_private()
        ctrl={'farmer':['DROP'],'hands':[],'market':[]}
        ali={'farmer':['DROP'],'hands':[],'market':[['SELL','WHEAT',2]]}
        picked=select_action(obs,ctrl,ali)
        expected=sale_path('WHEAT',obs['market']['inventory']['WHEAT'],2,game.market_price)[0]
        result=transition(obs,other,picked,pas,game)
        actual=result[seat]['reward']-3000
        if actual!=expected or result[seat]['status']!='DONE' or result[seat]['private']['shed']['WHEAT']!=0:
            raise ValueError('Final sale mechanics mismatch')
        rows.append({'seat':seat,'product':'WHEAT','expected':expected,'observed':actual,'kind':'last_sale','passed':True})
    write(OUT/'mechanics.json',rows);log('MECHANICS_PASSED',checks=len(rows),interpreter_calls=38)
    return rows


def measured(actor,obs,label,key,step):
    before=digest(obs);arg=deepcopy(obs)
    t=time.perf_counter();action=actor(arg);ms=(time.perf_counter()-t)*1000
    sample={'key':key,'step':step,'actor':label,'callback_ms':ms,'action':action}
    write(OUT/'latest_callback.json',sample)
    with (OUT/'callback_trace.jsonl').open('a') as f:f.write(json.dumps(sample)+'\n');f.flush()
    if digest(arg)!=before or digest(obs)!=before:raise ValueError('Actor mutated observation')
    if not math.isfinite(ms) or ms<0 or ms>500:raise RuntimeError('500 ms callback gate breached; sample saved')
    return action,ms


def evaluate_episode(payload,key,game,mods,actor_factory=None,rival_factory=None):
    from timing_features import FinalSalePolicy,extract
    if rival_factory is None:
        from kaggriculture_livestock.policy import LivestockPolicy
        rival_factory=LivestockPolicy.from_state_dict
    cont=mods['continuation'];records=cont.index_episode(payload);seat=key['seat']
    policy=(actor_factory or FinalSalePolicy)(key['arm']);policy.prime_recorded_clock(695,seat)
    features=[];latencies=[];prefix=0
    for step in range(696,719):
        obs=cont.legal_observation(records[(step,seat)]['observation'])
        action,ms=measured(policy,obs,'candidate',key,step)
        latencies.append({'step':step,'actor':'candidate','callback_ms':ms})
        control=policy.last_diagnostics['control_action']
        if control!=records[(step,seat)]['action']:raise ValueError('Control no longer matches source action')
        if step<718:
            if action!=records[(step,seat)]['action']:raise ValueError('Gate changed the shared prefix')
            prefix+=1
        if any(action[k]!=control[k] for k in ('farmer','hands')):raise ValueError('Unexpected farm intervention')
        post=mods['callback'].apply_farm_actions(obs,control,game)
        before=digest((obs,post))
        tick=time.perf_counter();vector=extract(obs,post['private'],game);feature_ms=(time.perf_counter()-tick)*1000
        if digest((obs,post))!=before:raise ValueError('Extractor mutated input')
        features.append({'step':step,'extractor_ms':feature_ms,**vector})
    other=cont.legal_observation(records[(718,1-seat)]['observation'])
    rival=rival_factory({'arm':'fertilizer','last_step':717,'player':1-seat})
    rival_action,ms=measured(rival,other,'opponent',key,718)
    latencies.append({'step':718,'actor':'opponent','callback_ms':ms})
    if rival_action!=records[(718,1-seat)]['action']:raise ValueError('Live opponent differs at shared final state')
    results={}
    for name,a in (('control',control),('guarded',action)):
        result=mods['run_cash'].isolated_transition(obs,other,a,rival_action,game)
        if name=='control':mods['run_cash'].assert_source_transition(result,None,payload['rewards'],718)
        results[name]=cont.terminal_metrics(result,seat,game.PRODUCTS)
    row={**key,'role':'primary' if key['arm']=='coordinated' else 'negative_control',
         'prefix_action_parity_checks':prefix,'source_final_reward_parity':True,
         'final_market_changed':action['market']!=control['market'],
         'shared_final_state_sha256':digest([obs,other])}
    for field in ('coins','opponent_coins','coin_margin','local_match_score','residual_product_units'):
        row[field+'_control']=results['control'][field];row[field+'_guarded']=results['guarded'][field]
        row[field+'_delta']=results['guarded'][field]-results['control'][field]
    if row['role']=='negative_control' and (action!=control or any(row[f+'_delta']!=0 for f in ('coins','opponent_coins','coin_margin','local_match_score','residual_product_units'))):
        raise ValueError('Sequential negative control diverged')
    return {'key':key,'result':row,'features':features,'latencies':latencies,
            'final_control_action':control,'final_guarded_action':action,'final_opponent_action':rival_action,
            'source_final_state_reconstructed':True,'interpreter_calls':2}


def choose_decision(rows,complete):
    primary=[r for r in rows if r['role']=='primary']
    if any(r['coins_delta']<0 or r['coin_margin_delta']<0 or r['local_match_score_delta']<0 for r in primary):return 'STOP_NEGATIVE_FINAL_EFFECT'
    if not complete:return 'INCOMPLETE_NO_GENERALIZATION_CLAIM'
    if not any(r['final_market_changed'] for r in primary):return 'STOP_NO_ACTIVATION'
    if not any(r['coins_delta']>0 or r['coin_margin_delta']>0 or r['local_match_score_delta']>0 for r in primary):return 'STOP_NO_FINAL_BENEFIT'
    return 'PROMISING_DEVELOPMENT_ONLY_FRESH_VALIDATION_REQUIRED'


def run_tests():
    suite=unittest.defaultTestLoader.discover(str(BASE/'tests'))
    r=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
    d={'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped)}
    write(OUT/'tests.json',d)
    if not r.wasSuccessful() or r.skipped:raise RuntimeError('Unit tests failed or skipped')
    return d


def worker(args):
    def deadline(signum, frame):
        raise TimeoutError('180-second independent worker deadline')
    if hasattr(signal, 'SIGALRM'):
        signal.signal(signal.SIGALRM, deadline);signal.alarm(180)
    started=time.monotonic();tests=run_tests();root,game,mods=preflight(args)
    mech=mechanics(game,mods['run_cash'].isolated_transition)
    from kaggriculture_research.artifacts import load_checkpoint
    from kaggriculture_staffing.experiment import validate_episode
    progress=read(root/'reports/staffing_progress.json');items=progress['artifact_manifest']
    expected={(1601,0,'coordinated'),(1601,1,'coordinated'),(1602,0,'coordinated'),
              (1601,0,'sequential'),(1601,1,'sequential'),(1602,0,'sequential'),(1602,1,'sequential')}
    if len(items)!=7 or {(a['seed'],a['seat'],a['arm']) for a in items}!=expected:
        raise ValueError('Do not reconstruct missing original episode')
    fp=digest({'code':code_hash(BASE),'protocol':sha(BASE/'PROTOCOL.json'),'source':COMMIT,'engine':ENGINE,
               'previous_report':sha(args.previous/'outputs/report.json'),'source_progress':sha(root/'reports/staffing_progress.json')})
    done=[]
    for ix,a in enumerate(sorted(items,key=lambda x:(x['seed'],x['seat'],x['arm'])),1):
        key={k:a[k] for k in ('seed','seat','opponent','arm')};ident=digest(key)[:20]
        if key['opponent']!='livestock_fertilizer':raise ValueError('Unexpected source opponent')
        source=inside(root,a['path'])
        if sha(source)!=a['sha256']:raise ValueError('Episode hash changed')
        cache=OUT/'checkpoints'/f'{ident}.json.gz';cpf=digest({'run':fp,'source':a['sha256'],'key':key})
        result=load_cache(cache,cpf);reused=result is not None
        if result is None:
            payload=load_checkpoint(source,{**progress['lineage'],**key})
            if payload is None:raise ValueError('Source lineage mismatch')
            validate_episode(payload,key)
            result=evaluate_episode(payload,key,game,mods)
            save_cache(cache,cpf,result)
        if result['result']['prefix_action_parity_checks']!=22 or any(not 0<=r['callback_ms']<=500 for r in result['latencies']):
            raise ValueError('Checkpoint acceptance gate failed')
        done.append({**result,'reused':reused})
        log('EPISODE_REUSED' if reused else 'EPISODE_CHECKPOINT_SAVED',episode=ix,total=7,
            **key,coins_delta=result['result']['coins_delta'],match_delta=result['result']['local_match_score_delta'])
        write(OUT/'progress.json',{'completed':len(done),'planned':7,'rows':[x['result'] for x in done]})
        if choose_decision([x['result'] for x in done],False)=='STOP_NEGATIVE_FINAL_EFFECT':break
    summarize(done,tests,fp,started)


def summarize(done,tests,fp,started):
    import pandas as pd
    rows=[x['result'] for x in done];table=pd.DataFrame(rows)
    features=pd.DataFrame([{**d['key'],**r} for d in done for r in d['features']])
    latency=pd.DataFrame([{**d['key'],**r} for d in done for r in d['latencies']])
    cols=[c for c in features if c.startswith('sale_timing.')]
    registry=pd.DataFrame([{'feature':c,'distinct_values':int(features[c].nunique()),'minimum':float(features[c].min()),
                           'maximum':float(features[c].max()),'nonzero_fraction':float(features[c].ne(0).mean()),
                           'status':'candidate_activation_not_predictive_importance'} for c in cols])
    exports={'final_comparisons.csv':table,'timing_features.csv':features,'latency.csv':latency,'feature_registry.csv':registry}
    for n,f in exports.items():write_bytes(OUT/n,f.to_csv(index=False).encode())
    report={'status':STATUS,'decision':choose_decision(rows,len(rows)==7),'utc':utc(),'code_sha256':code_hash(BASE),'fingerprint':fp,
        'source_commit':COMMIT,'engine_sha256':ENGINE,'completed_pairs':len(rows),'planned_pairs':7,
        'primary_pairs':sum(r['role']=='primary' for r in rows),'negative_controls':sum(r['role']=='negative_control' for r in rows),
        'source_seed_blocks':len({r['seed'] for r in rows}),'source_opponents':['livestock_fertilizer'],
        'source_prefix_action_parity_checks':sum(r['prefix_action_parity_checks'] for r in rows),
        'source_final_reward_checks':len(rows),'reused_episodes':sum(d['reused'] for d in done),
        'new_research_interpreter_calls':sum(d['interpreter_calls'] for d in done if not d['reused']),
        'represented_research_interpreter_calls':sum(d['interpreter_calls'] for d in done),'mechanics_interpreter_calls':38,
        'feature_rows':len(features),'new_candidate_descriptors':len(cols),'candidate_callback_max_ms':float(latency[latency.actor=='candidate'].callback_ms.max()),
        'feature_extractor_max_ms':float(features.extractor_ms.max()),'tests':tests,'elapsed_seconds':time.monotonic()-started,
        'primary_results':[r for r in rows if r['role']=='primary'],
        'new_complete_games':0,'models_fit':0,'official_submission_score':None,'official_metric_effect_measured':False,
        'github_updated':False,'cloud_resources_modified':False,'prior_outputs_modified':False,'feature_engineering_complete':False,
        'limitations':['Chosen after development results; these are not untouched validation groups.',
          'Terminal counterfactual is a suffix endpoint only because all earlier candidate actions are exactly unchanged.',
          'Prefix checks recompute 154 policy callbacks at most, not simulator seasons; final evaluator has both private views, actors never do.',
          'At most three coordinated efficacy pairs in two seed blocks and one related opponent; sequential controls are not efficacy replications.',
          'Missing seed1602 seat1 coordinated source stays missing. No confidence intervals or turn-level significance tests.',
          'Known-demand paths exclude unknown future trades and shops. Logged timing candidates are not separately outcome-ablated.',
          'The only action-changing feature is the fixed final-sale deadline. The callback still inherits the three-hand restriction.',
          'Local timing is not hosted Kaggle acceptance. Coins and match indicators are not leaderboard ratings.',
          'Local checkpoints have checksums/readback; no automatic S3 backup. Download the results bundle.'],
        'output_sha256':{n:sha(OUT/n) for n in exports}}
    write(OUT/'report.json',report);log(STATUS,decision=report['decision'],completed_pairs=len(rows))


def supervise(args):
    status=OUT/'run_status.json'
    if status.exists():
        s=read(status)
        if s['status']=='COMPLETED':
            r=read(OUT/'report.json')
            if s['report_sha256']!=sha(OUT/'report.json') or r['code_sha256']!=code_hash(BASE):raise ValueError('Completed receipt mismatch')
            for n,h in r['output_sha256'].items():
                if sha(inside(OUT,n))!=h:raise ValueError('Completed output changed')
            verify_previous(args.previous,args.cash)
            log('COMPLETED_RESULT_REUSED',decision=r['decision']);return
        raise RuntimeError('Prior attempt is active/failed/interrupted. Bundle it; do not retry unchanged.')
    OUT.mkdir(exist_ok=True);write(status,{'status':'RUNNING','utc':utc()})
    cmd=[sys.executable,str(BASE/'run_timing.py'),'_worker','--previous',str(args.previous),'--cash',str(args.cash),'--resume',str(args.resume)]
    t=time.monotonic();beat=t
    child=subprocess.Popen(cmd,start_new_session=True)
    try:
        while child.poll() is None:
            now=time.monotonic()
            if now-t>180:raise TimeoutError('180-second worker cap reached')
            if now-beat>=10:log('HEARTBEAT',elapsed_seconds=round(now-t,1));beat=now
            time.sleep(.25)
        if child.returncode:raise RuntimeError('Worker failed. Bundle diagnostics; do not retry unchanged.')
        write(status,{'status':'COMPLETED','utc':utc(),'report_sha256':sha(OUT/'report.json')})
    except BaseException:
        if child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=2)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        write(status,{'status':'FAILED','utc':utc()});raise


def bundle():
    paths=[]
    for p in OUT.rglob('*'):
        if p.is_file() and not p.is_symlink() and p.suffix in ('.json','.csv','.jsonl','.gz','.html','.txt'):
            if p.stat().st_size>30_000_000:raise ValueError('Unexpectedly large output; inspect before bundling')
            paths.append(p)
    paths += [BASE/'10_sale_timing_feature_ablation.ipynb',BASE/'PROTOCOL.json',BASE/'reference/input_review.json',BASE/'FEATURE_RESEARCH.md',BASE/'LOCAL_VALIDATION.json']
    manifest={'utc':utc(),'files':{str(p.relative_to(BASE)):sha(p) for p in paths if p.exists()}}
    dest=BASE/'kaggriculture_sale_timing_results.zip'
    fd,tmp=tempfile.mkstemp(prefix='.bundle-',dir=BASE);os.close(fd)
    try:
        with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
            for p in paths:
                if p.exists():z.write(p,str(p.relative_to(BASE)))
            z.writestr('BUNDLE_MANIFEST.json',json.dumps(manifest,indent=2))
        os.replace(tmp,dest)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    print('RESULTS_BUNDLE:',dest,flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['run','_worker','bundle','tests','diagnose'])
    ap.add_argument('--previous',type=Path,default=Path.home()/'kaggriculture_terminal_ablation')
    ap.add_argument('--cash',type=Path,default=Path.home()/'kaggriculture_cash_realization')
    ap.add_argument('--resume',type=Path,default=Path.home()/'kaggriculture_manual_resume')
    args=ap.parse_args()
    try:
        if args.command=='run':supervise(args)
        elif args.command=='_worker':worker(args)
        elif args.command=='bundle':bundle()
        elif args.command=='diagnose':verify_previous(args.previous,args.cash)
        else:run_tests()
    except BaseException as exc:
        OUT.mkdir(exist_ok=True);write(OUT/('failure_worker.json' if args.command=='_worker' else 'failure.json'),
          {'utc':utc(),'command':args.command,'error':str(exc),'traceback':traceback.format_exc()})
        raise
if __name__=='__main__':
    def terminate(signum, frame):
        raise KeyboardInterrupt('Termination requested; preserving checkpoints')
    signal.signal(signal.SIGTERM, terminate)
    main()
