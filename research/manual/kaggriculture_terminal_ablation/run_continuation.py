"""Bounded manual notebook-09 runner. No network, installs, Git writes or AWS APIs."""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime,timezone
import gzip
import hashlib
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
from types import SimpleNamespace
import unittest
import zipfile

BASE=Path(__file__).resolve().parent
OUT=BASE/'outputs'
COMMIT='7194116dfc92a8663139611233b5a221dad431a4'
ENGINE='bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e'
STATUS='TERMINAL_CASH_EXPERIMENT_COMPLETE'
PREVIOUS=Path.home()/'kaggriculture_cash_realization'
RESUME=Path.home()/'kaggriculture_manual_resume'


def utc(): return datetime.now(timezone.utc).isoformat()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(x): return hashlib.sha256(canonical(x)).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()
def inside(root,rel):
    p=(Path(root)/rel).resolve()
    if not p.is_relative_to(Path(root).resolve()): raise ValueError('Artifact path escapes root')
    return p
def write_bytes(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.checkpoint-',dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f: f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
def write(p,x): write_bytes(p,json.dumps(x,indent=2,sort_keys=True,allow_nan=False).encode()+b'\n')
def code_hash(root=BASE):
    return digest({str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*.py')) if 'outputs' not in p.parts})
def log(stage,**kw):
    OUT.mkdir(exist_ok=True)
    row={'utc':utc(),'stage':stage,**kw}
    with (OUT/'events.jsonl').open('a') as f: f.write(json.dumps(row)+'\n');f.flush()
    print(json.dumps(row),flush=True)
def save_cache(path,fp,payload):
    if path.exists(): raise ValueError('Refusing to overwrite an existing branch checkpoint')
    body={'fingerprint':fp,'payload':payload};body['checksum']=digest(body)
    write_bytes(path,gzip.compress(canonical(body),mtime=0))
    if load_cache(path,fp)!=payload: raise ValueError('Checkpoint readback differs')
def load_cache(path,fp):
    if not path.exists(): return None
    body=json.loads(gzip.decompress(path.read_bytes()));h=body.pop('checksum')
    if digest(body)!=h or body['fingerprint']!=fp: raise ValueError('Checkpoint hash/lineage differs; preserve it')
    return body['payload']


def verify_previous(previous):
    manifest=read(BASE/'reference/previous_code_manifest.json')
    for rel,h in manifest.items():
        if sha(inside(previous,rel))!=h: raise ValueError('Notebook08 implementation changed: '+rel)
    r=read(previous/'outputs/report.json');s=read(previous/'outputs/run_status.json')
    expected=read(BASE/'reference/input_review.json')['report_sha256']
    if sha(previous/'outputs/report.json')!=expected: raise ValueError('Notebook08 report differs from the reviewed return')
    if r['status']!='POST_ACTION_CASH_AUDIT_PASSED' or s['status']!='PASSED': raise ValueError('Notebook08 is not passed')
    if s['report_sha256']!=expected or r['code_sha256']!=code_hash(previous): raise ValueError('Notebook08 pass/code mismatch')
    for rel,h in r['output_sha256'].items():
        if sha(inside(previous/'outputs',rel))!=h: raise ValueError('Notebook08 export differs: '+rel)
    return r


def import_previous(previous):
    sys.path.insert(0,str(previous))
    modules={name:importlib.import_module(name) for name in ('callback','cash_features','run_cash')}
    for name,mod in modules.items():
        if Path(mod.__file__).resolve()!=previous.resolve()/(name+'.py'): raise ValueError('Wrong module imported: '+name)
    return modules


def preflight(args):
    verify_previous(args.previous)
    source=read(args.resume/'state/source.json');runtime=read(args.resume/'state/runtime.json')
    ready=read(args.resume/'state/readiness.json');restore=read(args.resume/'state/restore.json')
    if any(x.get('status')!='PASSED' for x in (source,runtime,restore)):
        raise ValueError('Existing readiness receipts are not passed')
    if sys.version_info[:2]!=(3,12) or Path(sys.executable).absolute()!=Path(runtime['executable']).absolute():
        raise ValueError('Select Kaggriculture Manual (verified source); do not install a new runtime')
    repo=Path(source['repo']).resolve()
    def git(*words): return subprocess.check_output(['git',*words],cwd=repo,text=True,timeout=10).strip()
    if git('rev-parse','HEAD')!=COMMIT: raise ValueError('Checkout moved; preserve changes, do not reset')
    if git('status','--porcelain','--untracked-files=no'): raise ValueError('Tracked changes require review')
    for rel,h in ready['source_files'].items():
        if sha(inside(repo,rel))!=h: raise ValueError('Reviewed source changed: '+rel)
    sys.path.insert(0,str(repo/'src'))
    from kaggriculture_research import environment
    if not Path(environment.__file__).resolve().is_relative_to(repo/'src'): raise ValueError('Wrong project import path')
    if environment.engine_manifest()['files']['envs/kaggriculture/kaggriculture.py']!=ENGINE:
        raise ValueError('Pinned official interpreter changed')
    root=Path(restore['private_root']).resolve()
    if restore['episode_count']!=7 or len(restore['downloaded_or_reused'])!=10: raise ValueError('Recovery scope changed')
    for row in restore['downloaded_or_reused']:
        p=inside(root,row['path'])
        if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']: raise ValueError('Source episode changed: '+row['path'])
    modules=import_previous(args.previous)
    receipt={'status':'PASSED','utc':utc(),'source_commit':COMMIT,'engine_sha256':ENGINE,
             'code_sha256':code_hash(),'prior_report_sha256':sha(args.previous/'outputs/report.json'),
             'private_root':str(root),'repo':str(repo),'verified_objects':10}
    write(OUT/'preflight.json',receipt);log('PREFLIGHT_PASSED',verified_objects=10)
    return root,environment.game,modules,receipt


def run_tests():
    res=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(unittest.defaultTestLoader.discover(str(BASE/'tests')))
    receipt={'tests':res.testsRun,'failures':len(res.failures),'errors':len(res.errors),'skipped':len(res.skipped)}
    write(OUT/'tests.json',receipt)
    if not res.wasSuccessful() or res.skipped: raise RuntimeError('Unit tests failed or skipped')
    return receipt


def mechanics(game,transition):
    """Require price-aware absolute endpoint parity before any research branches."""
    from continuation import project_next
    from mechanics_checks import KINDS, evaluate_fixture
    rows=[]
    for kind in KINDS:
        row=evaluate_fixture(game,transition,project_next,kind)
        rows.append(row)
        # Save expected/observed endpoints and transition traces before gating.
        write(OUT/'mechanics.json',rows)
        log('MECHANICS_FIXTURE',fixture=kind,initial_quote=row['initial_quote'],
            expected_delta=row['expected_delta'],observed_delta=row['terminal_cash_delta'],
            passed=row['passed'])
        if not row['passed']:
            raise ValueError('Continuation fixture endpoint incorrect: '+kind+
                             '; see outputs/mechanics.json for expected/observed cash and quotes')
    log('MECHANICS_PASSED',fixtures=len(rows),interpreter_calls=sum(r['interpreter_calls'] for r in rows))
    return rows


def analyze(root,game,modules,fp):
    from continuation import rollout,pair_results,decision,digest as state_digest
    from terminal_context import extract
    from kaggriculture_research.artifacts import load_checkpoint
    from kaggriculture_staffing.experiment import validate_episode
    progress=read(root/'reports/staffing_progress.json');items=progress['artifact_manifest']
    if progress['completed_games']!=7 or progress['complete'] or len(items)!=7:
        raise ValueError('Expected the preserved seven-game, incomplete pilot')
    expected={(1601,0,'coordinated'),(1601,1,'coordinated'),(1602,0,'coordinated'),
              (1601,0,'sequential'),(1601,1,'sequential'),(1602,0,'sequential'),(1602,1,'sequential')}
    if {(x['seed'],x['seat'],x['arm']) for x in items}!=expected or len({x['path'] for x in items})!=7:
        raise ValueError('Source inventory changed; do not reconstruct the missing original episode')
    pairs=[];branches=[];inventory=[]
    order=sorted(items,key=lambda x:(x['seed'],x['seat'],x['arm']))
    for ix,a in enumerate(order,1):
        key={k:a[k] for k in ('seed','seat','opponent','arm')};ident=digest(key)[:20]
        p=inside(root,a['path'])
        if sha(p)!=a['sha256']: raise ValueError('Source checkpoint hash changed')
        payload=load_checkpoint(p,{**progress['lineage'],**key})
        if payload is None: raise ValueError('Source lineage mismatch')
        validate_episode(payload,key)
        inventory.append({**key,'episode_id':ident,'source_sha256':a['sha256'],
                          'preterminal_sha256':payload['preterminal_sha256']})
        pair={}
        for variant in ('control','aligned'):
            cache=OUT/'checkpoints'/f'{ident}-{variant}.json.gz'
            branchfp=digest({'run':fp,'key':key,'source':a['sha256'],'variant':variant})
            saved=load_cache(cache,branchfp)
            was_reused=saved is not None
            if saved is None:
                log('BRANCH_STARTED',episode=ix,total=7,variant=variant,source_arm=key['arm'])
                def emit(stage,data):
                    row={'utc':utc(),'episode_id':ident,'variant':variant,'stage':stage,**data}
                    with (OUT/'callback_trace.jsonl').open('a') as f:
                        f.write(json.dumps(row,allow_nan=False)+'\n');f.flush()
                    if stage=='CALLBACK_MEASURED': write(OUT/'latest_callback.json',row)
                saved=rollout(payload,key,variant,game,modules['run_cash'].isolated_transition,
                    modules['run_cash'].assert_source_transition,emit,context_extractor=extract)
                save_cache(cache,branchfp,saved)
                log('BRANCH_CHECKPOINT_SAVED',episode=ix,total=7,variant=variant,
                    actual_final_coins=saved['metrics']['coins'],checkpoint_sha256=sha(cache))
            else:
                log('BRANCH_REUSED',episode=ix,total=7,variant=variant)
            # Cached timing remains measured data; a cache hit cannot erase failed samples.
            for r in saved['trace']:
                for f in ('candidate_callback_ms','opponent_callback_ms','same_state_control_callback_ms'):
                    if not 0<=r[f]<=500: raise ValueError('Cached callback gate failed')
            pair[variant]={**saved,'reused_from_checkpoint':was_reused}
        row=pair_results(pair['control'],pair['aligned']);row['episode_id']=ident
        pairs.append(row);branches.extend(pair.values())
        write(OUT/'paired_progress.json',{'completed_pairs':len(pairs),'planned_pairs':7,'pairs':pairs})
        log('PAIR_COMPLETE',episode=ix,total=7,role=row['role'],coins_delta=row['coins_delta'],
            coin_margin_delta=row['coin_margin_delta'],match_score_delta=row['local_match_score_delta'])
        if decision(pairs,False)=='STOP_NEGATIVE_TERMINAL_EFFECT':
            log('EARLY_STOP',reason='Negative terminal effect; completed branches preserved');break
    return pairs,branches,inventory


def summarize(pairs,branches,inventory,tests,pf,fp,started):
    import pandas as pd
    from continuation import decision
    def meta(b): return {**b['key'],'episode_id':digest(b['key'])[:20]}
    table=pd.DataFrame(pairs)
    trace=pd.DataFrame([{**meta(b),**r} for b in branches for r in b['trace']])
    features=pd.DataFrame([{**meta(b),**r} for b in branches for r in b['features']])
    cols=[c for c in features if c.startswith(('cash.','terminal_context.'))]
    registry=pd.DataFrame([{'feature':c,'distinct_values':int(features[c].nunique()),
        'minimum':float(features[c].min()),'maximum':float(features[c].max()),
        'nonzero_fraction':float(features[c].ne(0).mean()),
        'role':'unchanged_cash_intervention_representation' if c.startswith('cash.') else 'new_candidate_diagnostic_only',
        'value_status':'NO_INDIVIDUAL_PREDICTIVE_ABLATION'} for c in cols])
    primary=table[table.role=='primary_intervention']
    seed_rows=[]
    for seed,g in primary.groupby('seed'):
        seed_rows.append({'seed':int(seed),'evaluated_seats':','.join(map(str,sorted(g.seat))),
            'primary_pairs':len(g),'mean_coin_delta':float(g.coins_delta.mean()),
            'min_coin_delta':float(g.coins_delta.min()),'max_coin_delta':float(g.coins_delta.max()),
            'mean_margin_delta':float(g.coin_margin_delta.mean()),
            'mean_local_match_delta':float(g.local_match_score_delta.mean()),
            'status':'descriptive_development_block_not_independent_turn_samples'})
    by_seed=pd.DataFrame(seed_rows)
    exports={'paired_results.csv':table,'trajectory.csv':trace,'causal_features.csv':features,
             'feature_registry.csv':registry,'source_inventory.csv':pd.DataFrame(inventory),
             'primary_by_seed.csv':by_seed}
    for name,f in exports.items(): write_bytes(OUT/name,f.to_csv(index=False).encode())
    complete=len(pairs)==7
    r={'status':STATUS,'utc':utc(),'decision':decision(pairs,complete),'source_commit':COMMIT,
       'engine_sha256':ENGINE,'code_sha256':code_hash(),'fingerprint':fp,
       'execution_mode':'AWS_REACTIVE_FINAL_DAY_CONTINUATIONS','planned_pairs':7,'completed_pairs':len(pairs),
       'all_planned_pairs_completed':complete,'primary_pairs':len(primary),
       'negative_control_pairs':int((table.role=='negative_control').sum()),
       'completed_branches':len(branches),'represented_suffix_interpreter_calls':sum(b['transitions'] for b in branches),
       'new_suffix_interpreter_calls':sum(b['transitions'] for b in branches if not b.get('reused_from_checkpoint',False)),
       'branches_reused_from_checkpoint':sum(b.get('reused_from_checkpoint',False) for b in branches),
       'protocol_sha256':sha(BASE/'PROTOCOL.json'),
       'mechanics_interpreter_calls':12,'source_control_transition_parity_checks':sum(b['control_recorded_transition_parity_checks'] for b in branches),
       'source_seed_blocks':int(primary.seed.nunique()),'source_opponents':['livestock_fertilizer'],
       'primary_positive_coin_pairs':int((primary.coins_delta>0).sum()),
       'primary_zero_coin_pairs':int((primary.coins_delta==0).sum()),
       'primary_negative_coin_pairs':int((primary.coins_delta<0).sum()),
       'primary_coin_deltas':primary[['seed','seat','coins_delta','coin_margin_delta','local_match_score_delta']].to_dict('records'),
       'candidate_callback_max_ms':float(trace.candidate_callback_ms.max()),
       'opponent_callback_max_ms':float(trace.opponent_callback_ms.max()),
       'same_state_attribution_all_passed':bool(trace.same_state_attribution_passed.all()),
       'opponent_actions_recomputed_on_each_branch':True,'recorded_opponent_tape_used_for_control_validation_only':True,
       'new_terminal_context_candidates':12,'total_causal_descriptors':len(cols),
       'new_context_candidates_used_to_change_actions':False,
       'new_complete_games_from_initial_state':0,'terminal_continuation_endpoints_measured':True,
       'full_season_generalization_established':False,'official_metric_effect_measured':False,
       'official_submission_score':None,'feature_completion_gate':'OPEN',
       'validation_or_holdout_used':False,'models_fit':0,'github_updated':False,
       'aws_resources_modified':False,'s3_upload_performed':False,'previous_artifacts_modified':False,
       'tests':tests,'elapsed_seconds':time.monotonic()-started,
       'limitations':['Exploratory development study selected after notebook08; not preregistered before those observations.',
          'Seven preserved suffixes from two seed blocks and one related opponent; three coordinated primary pairs and four sequential negative controls.',
          'The missing coordinated seed1602/seat1 source episode stays missing. Negative controls are not additional efficacy trials.',
          'Seats can be symmetric; no turn-level inference, confidence intervals or claim of independent seven-game validation.',
          'A fresh live opponent responds according to its unchanged source policy; this is not retraining or a new independent opponent family.',
          'Frozen action callback still rejects more than three hands on either public farm.',
          'Twelve new terminal-context candidates are activation-only; conditional values ignore shared capacity and rival orders.',
          'Persistent local checkpoints plus a user-downloaded bundle, not S3 readback or an off-instance automatic backup.',
          'Local callback timings are not hosted Kaggle acceptance. No leaderboard rating can be inferred.'],
       'output_sha256':{name:sha(OUT/name) for name in exports}}
    write(OUT/'report.json',r);log(STATUS,decision=r['decision'],completed_pairs=len(pairs))
    return r


def worker(args):
    started=time.monotonic()
    # Load the exact prior helpers for context unit tests, without importing the engine.
    verify_previous(args.previous);import_previous(args.previous)
    tests=run_tests();root,game,modules,pf=preflight(args)
    fp=digest({'code':code_hash(),'protocol':sha(BASE/'PROTOCOL.json'),'source':COMMIT,'engine':ENGINE,
               'prior_report':pf['prior_report_sha256'],'source_progress':sha(root/'reports/staffing_progress.json')})
    mechanics(game,modules['run_cash'].isolated_transition)
    pairs,branches,inventory=analyze(root,game,modules,fp)
    summarize(pairs,branches,inventory,tests,pf,fp,started)


def supervise(command,seconds):
    start=time.monotonic();last=start
    child=subprocess.Popen(command,cwd=BASE,start_new_session=True,
        env={**os.environ,'PYTHONUNBUFFERED':'1','PYTHONDONTWRITEBYTECODE':'1'})
    try:
        while child.poll() is None:
            now=time.monotonic()
            if now-start>=seconds:
                os.killpg(child.pid,signal.SIGTERM)
                try: child.wait(timeout=2)
                except subprocess.TimeoutExpired: os.killpg(child.pid,signal.SIGKILL);child.wait()
                raise TimeoutError('180-second work cap reached; existing branch checkpoints preserved')
            if now-last>=10: log('HEARTBEAT',elapsed_seconds=round(now-start,1));last=now
            time.sleep(.1)
    except BaseException:
        if child.poll() is None: os.killpg(child.pid,signal.SIGKILL);child.wait()
        raise
    if child.returncode: raise RuntimeError('Worker failed. Bundle saved diagnostics; do not retry unchanged.')


def verify_result():
    r=read(OUT/'report.json');s=read(OUT/'run_status.json')
    if r['status']!=STATUS or r['code_sha256']!=code_hash() or s['status']!='COMPLETED': raise ValueError('No matching completed experiment')
    if s['report_sha256']!=sha(OUT/'report.json'): raise ValueError('Report receipt hash mismatch')
    if r['protocol_sha256']!=sha(BASE/'PROTOCOL.json'): raise ValueError('Experiment protocol changed')
    for rel,h in r['output_sha256'].items():
        if sha(inside(OUT,rel))!=h: raise ValueError('Output hash mismatch: '+rel)
    return r


def consume_reviewed_resume():
    """Allow one code-bound restart of the specifically diagnosed fixture error."""
    permission=OUT/'resume_authorization.json'
    used=OUT/'resume_authorization_used.json'
    if not permission.is_file() or used.exists():
        raise RuntimeError('Previous attempt requires diagnosis; no unchanged automatic retry')
    grant=read(permission)
    if grant.get('code_sha256') != code_hash():
        raise RuntimeError('Reviewed restart is not bound to these source files')
    for name,key in (('run_status.json','failed_status_sha256'),
                     ('failure_worker.json','failed_worker_sha256')):
        if sha(OUT/name) != grant.get(key):
            raise RuntimeError('Failure evidence changed after review; do not retry')
    if read(OUT/'run_status.json').get('status') != 'FAILED':
        raise RuntimeError('Restart permission requires the diagnosed FAILED state')
    failure=read(OUT/'failure_worker.json').get('traceback','')
    if 'Continuation fixture endpoint incorrect' not in failure or 'mechanics' not in failure:
        raise RuntimeError('Failure differs from the reviewed mechanics error')
    if (OUT/'report.json').exists() or any((OUT/'checkpoints').glob('*.json.gz')):
        raise RuntimeError('Existing branch evidence must be reviewed; no cross-code cache reuse')
    write(used,{**grant,'consumed_at_utc':utc()})
    log('REVIEWED_MECHANICS_RESTART_AUTHORIZED',update_id=grant['update_id'])


def run(args):
    import fcntl
    OUT.mkdir(exist_ok=True)
    with (OUT/'.run.lock').open('a+') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('Another notebook09 process is active')
        if (OUT/'run_status.json').exists():
            s=read(OUT/'run_status.json')
            if s['status']=='COMPLETED': preflight(args);r=verify_result();log('EXISTING_RESULT_REUSED',decision=r['decision']);return
            consume_reviewed_resume()
        write(OUT/'run_status.json',{'status':'RUNNING','utc':utc()})
        try:
            supervise([sys.executable,str(BASE/'run_continuation.py'),'_worker','--previous',str(args.previous),
                       '--resume',str(args.resume)],args.seconds)
            r=read(OUT/'report.json')
            if r['status']!=STATUS: raise ValueError('No completed experiment report')
            write(OUT/'run_status.json',{'status':'COMPLETED','utc':utc(),'report_sha256':sha(OUT/'report.json')})
            verify_result();log('NOTEBOOK09_COMPLETE',decision=r['decision'])
        except BaseException:
            write(OUT/'run_status.json',{'status':'FAILED','utc':utc()});raise


def bundle():
    OUT.mkdir(exist_ok=True)
    allowed=('report.json','run_status.json','tests.json','preflight.json','mechanics.json','paired_progress.json',
             'latest_callback.json','events.jsonl','callback_trace.jsonl','failure.json','failure_worker.json',
             'paired_results.csv','trajectory.csv','causal_features.csv','feature_registry.csv','source_inventory.csv',
             'primary_by_seed.csv','terminal_ablation.html','mechanics_check.html','resume_authorization.json','resume_authorization_used.json','update_receipt.json')
    paths=[(OUT/n,'outputs/'+n) for n in allowed if (OUT/n).is_file() and not (OUT/n).is_symlink()]
    paths += [(p,'outputs/checkpoints/'+p.name) for p in sorted((OUT/'checkpoints').glob('*.json.gz')) if not p.is_symlink()]
    paths += [(BASE/'09_terminal_cash_feature_ablation.ipynb','09_terminal_cash_feature_ablation.ipynb'),
              (BASE/'reference/input_review.json','reference/input_review.json'),(BASE/'PROTOCOL.json','PROTOCOL.json'),
              (BASE/'UPDATE_DIAGNOSIS.md','UPDATE_DIAGNOSIS.md'),
              (BASE/'UPDATE_VALIDATION.json','UPDATE_VALIDATION.json')]
    target=BASE/'kaggriculture_terminal_ablation_results.zip'
    tmp=target.with_suffix('.zip.tmp')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for p,name in paths: z.write(p,name)
        z.writestr('BUNDLE_MANIFEST.json',json.dumps({'utc':utc(),'files':{name:sha(p) for p,name in paths}},indent=2))
    os.replace(tmp,target)
    print(str(target),flush=True)
    return target


def main():
    def terminate(_signum,_frame): raise KeyboardInterrupt('Termination requested; preserve diagnostics')
    signal.signal(signal.SIGTERM,terminate)
    p=argparse.ArgumentParser();p.add_argument('command',choices=('run','_worker','bundle','verify'))
    p.add_argument('--previous',type=Path,default=PREVIOUS);p.add_argument('--resume',type=Path,default=RESUME)
    p.add_argument('--seconds',type=int,default=180);p.add_argument('--resume-after-review',action='store_true',help='Legacy argument; a code-bound one-use review receipt is still required')
    a=p.parse_args()
    if not 1<=a.seconds<=180: p.error('The maximum worker budget is 180 seconds')
    try:
        if a.command=='run': run(a)
        elif a.command=='_worker': worker(a)
        elif a.command=='bundle': bundle()
        else: print(json.dumps(verify_result(),indent=2))
    except BaseException:
        if a.command!='bundle': write(OUT/('failure_worker.json' if a.command=='_worker' else 'failure.json'),
                                      {'utc':utc(),'command':a.command,'traceback':traceback.format_exc()})
        raise

if __name__=='__main__': main()
