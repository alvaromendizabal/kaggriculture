"""Notebook 08: local, bounded, replay-only cash realization intervention.

No network calls, installations, AWS changes, Git writes, or full games. The
one-step evaluator alone receives both players' saved state/action, never policy
or feature construction. One-step cash deltas are not season/leaderboard gains.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
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
from types import SimpleNamespace
import unittest
import zipfile

BASE=Path(__file__).resolve().parent
OUT=BASE/'outputs'
PREVIOUS=Path.home()/'kaggriculture_action_features'
RESUME=Path.home()/'kaggriculture_manual_resume'
COMMIT='7194116dfc92a8663139611233b5a221dad431a4'
ENGINE='bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e'
STATUS='POST_ACTION_CASH_AUDIT_PASSED'
CALLBACK_LIMIT_MS=500.0


def utc(): return datetime.now(timezone.utc).isoformat()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(x): return hashlib.sha256(canonical(x)).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def contained(root,rel):
    p=(Path(root)/rel).resolve()
    if not p.is_relative_to(Path(root).resolve()): raise ValueError('Path escapes artifact root')
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
def save_cache(p,fp,payload):
    x={'fingerprint':fp,'payload':payload};x['checksum']=digest(x)
    write_bytes(p,gzip.compress(canonical(x),mtime=0))
def load_cache(p,fp):
    if not p.exists(): return None
    x=json.loads(gzip.decompress(p.read_bytes()));checksum=x.pop('checksum')
    if digest(x)!=checksum: raise ValueError('Cache checksum mismatch; preserve and inspect')
    if x['fingerprint']!=fp: raise ValueError('Checkpoint lineage changed; no overwrite')
    return x['payload']


def verify_prior(previous):
    for rel,h in read(BASE/'reference/previous_code_manifest.json').items():
        if sha(contained(previous,rel))!=h: raise ValueError('Notebook07 code differs: '+rel)
    report=read(previous/'outputs/report.json');state=read(previous/'outputs/run_status.json')
    if report['status']!='ACTION_FEATURE_AUDIT_PASSED' or state['status']!='PASSED':
        raise ValueError('Notebook07 has no passed receipt. Do not rerun it automatically.')
    if state['report_sha256']!=sha(previous/'outputs/report.json'): raise ValueError('Prior receipt hash differs')
    if report['code_sha256']!=code_hash(previous): raise ValueError('Prior code fingerprint differs')
    if report['source_commit']!=COMMIT or report['saved_observations']!=161 or report['source_episodes']!=7:
        raise ValueError('Unexpected notebook07 evidence scope')
    for rel,h in report['output_sha256'].items():
        if sha(contained(previous/'outputs',rel))!=h: raise ValueError('Prior export hash differs: '+rel)
    return report


def preflight(args):
    verify_prior(args.previous)
    source=read(args.resume/'state/source.json');ready=read(args.resume/'state/readiness.json')
    restored=read(args.resume/'state/restore.json');runtime=read(args.resume/'state/runtime.json')
    if any(x.get('status')!='PASSED' for x in (source,restored,runtime)):
        raise ValueError('Prior source, recovery or runtime receipt not passed')
    if sys.version_info[:2]!=(3,12) or Path(sys.executable).absolute()!=Path(runtime['executable']).absolute():
        raise ValueError('Use Kaggriculture Manual (verified source), not system Python')
    repo=Path(source['repo']).resolve()
    def git(*p): return subprocess.check_output(['git',*p],cwd=repo,text=True,timeout=10).strip()
    if git('rev-parse','HEAD')!=COMMIT: raise ValueError('Checkout changed; do not reset')
    if git('status','--porcelain','--untracked-files=no'): raise ValueError('Tracked changes must be preserved and reviewed')
    for rel,h in ready['source_files'].items():
        if sha(contained(repo,rel))!=h: raise ValueError('Source mismatch '+rel)
    sys.path.insert(0,str(repo/'src'))
    from kaggriculture_research import environment
    if not Path(environment.__file__).resolve().is_relative_to(repo/'src'): raise ValueError('Wrong source imports')
    manifest=environment.engine_manifest()
    if manifest['files']['envs/kaggriculture/kaggriculture.py']!=ENGINE: raise ValueError('Wrong engine')
    root=Path(restored['private_root']).resolve()
    if restored['episode_count']!=7 or len(restored['downloaded_or_reused'])!=10: raise ValueError('Wrong recovery scope')
    for obj in restored['downloaded_or_reused']:
        p=contained(root,obj['path'])
        if p.stat().st_size!=obj['bytes'] or sha(p)!=obj['sha256']: raise ValueError('Source evidence changed '+obj['path'])
    report={'status':'PASSED','utc':utc(),'repo':str(repo),'private_root':str(root),
            'source_commit':COMMIT,'engine_sha256':ENGINE,'code_sha256':code_hash(),
            'prior_report_sha256':sha(args.previous/'outputs/report.json'),'verified_objects':10}
    write(OUT/'preflight.json',report);log('PREFLIGHT_PASSED',verified_objects=10)
    return root,environment.game,report


class AttrDict(dict):
    def __getattr__(self,name):
        try: return self[name]
        except KeyError as exc: raise AttributeError(name) from exc


def isolated_transition(own_obs,rival_obs,own_action,rival_action,game):
    """EVALUATOR ONLY. One exact pinned final-day interpreter step on copied state.

    Saved rival private state and action are used to evaluate a fixed-action
    counterfactual. They are never passed to CashPolicy or extract_cash_features.
    Final-day steps 696..718 do not cross a random overnight transition.
    """
    seat=own_obs['player'];step=own_obs['day']*24+own_obs['hour']
    if not 696<=step<=718 or rival_obs['player']!=1-seat:
        raise ValueError('Expected paired final-day observations')
    for field in ('day','hour','farms','market','town'):
        if own_obs[field]!=rival_obs[field]: raise ValueError('Saved public states disagree: '+field)
    farms=deepcopy(own_obs['farms']);market=deepcopy(own_obs['market']);town=deepcopy(own_obs['town'])
    privates=[None,None];privates[seat]=deepcopy(own_obs['private']);privates[1-seat]=deepcopy(rival_obs['private'])
    actions=[None,None];actions[seat]=deepcopy(own_action);actions[1-seat]=deepcopy(rival_action)
    states=[SimpleNamespace(observation=SimpleNamespace(
        farms=farms,market=market,town=town,private=privates[i],player=i,
        step=step,day=29,hour=step%24),action=actions[i],status='ACTIVE',reward=0) for i in (0,1)]
    env=SimpleNamespace(done=False,configuration=AttrDict(episodeSteps=720,boardSize=10,
        turnsPerDay=24,shedCapacity=100,maxMarketOrdersPerTurn=10,farmHandCostMult=1,
        townShopSellInterval=4,townCenterSellInterval=24))
    game.interpreter(states,env)
    result=[]
    for s in states:
        o=s.observation
        result.append({'player':o.player,'day':o.day,'hour':o.hour,
            'farms':deepcopy(o.farms),'private':deepcopy(o.private),
            'market':deepcopy(o.market),'town':deepcopy(o.town),
            'status':s.status,'reward':s.reward})
    return result


def assert_source_transition(result,next_records,rewards,step):
    """Prove the evaluator reproduces frozen source transitions, not just our math."""
    if step<718:
        for seat in (0,1):
            expected=next_records[seat]['observation']
            for field in ('day','hour','farms','private','market','town'):
                if result[seat][field]!=expected[field]:
                    raise ValueError(f'Official source transition differs at {step} seat {seat}: {field}')
    else:
        for seat in (0,1):
            if result[seat]['status']!='DONE' or result[seat]['reward']!=rewards[seat]:
                raise ValueError('Final source reward/status reproduction differs')


def effects(own_obs,control,aligned,products):
    """Outcome labels live separately from causal feature tables."""
    seat=own_obs['player'];opponent=1-seat
    money=lambda results,p: float(results[p]['farms'][p]['money'])
    residual=lambda results: sum(n for inv in [results[seat]['private']['shed'],*results[seat]['private']['inventories']]
                                  for item,n in inv.items() if item in products)
    d=money(aligned,seat)-money(control,seat)
    dr=money(aligned,opponent)-money(control,opponent)
    return {'own_cash_control':money(control,seat),'own_cash_aligned':money(aligned,seat),
            'own_cash_delta':d,'opponent_cash_delta':dr,'coin_margin_delta':d-dr,
            'residual_units_control':residual(control),'residual_units_aligned':residual(aligned),
            'residual_units_delta':residual(aligned)-residual(control)}


def runtime_gate(records):
    if any(not math.isfinite(r[arm+'_callback_ms']) or r[arm+'_callback_ms'] < 0
           for r in records for arm in ('control','aligned')):
        raise ValueError('Invalid actual callback timing sample')
    maxima={arm:max((r[arm+'_callback_ms'] for r in records),default=0) for arm in ('control','aligned')}
    if any(v>CALLBACK_LIMIT_MS for v in maxima.values()):
        raise RuntimeError('500 ms complete-terminal-callback gate breached; actual samples saved')
    return maxima


def run_tests():
    suite=unittest.defaultTestLoader.discover(str(BASE/'tests'))
    res=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
    receipt={'tests':res.testsRun,'failures':len(res.failures),'errors':len(res.errors),'skipped':len(res.skipped)}
    write(OUT/'tests.json',receipt)
    if not res.wasSuccessful() or res.skipped: raise RuntimeError('Unit tests failed or skipped')
    return receipt


def mechanics(game):
    """Synthetic component fixtures; no earned trajectories or competition scores."""
    from cash_features import extract_cash_features,terminal_market_rule
    from callback import apply_farm_actions
    from kaggriculture_livestock.features import fertilizer_value
    rows=[]
    for case in range(5):
        own={'player':0,'day':29,'hour':22 if case==0 else 20,'step':718 if case==0 else 716,
             'farms':[game._new_farm(10,3000) for _ in (0,1)],'private':game._new_private(),
             'market':game._new_market(),'town':game._new_town()}
        own['private']['inventories'][0]={'WHEAT':3,'MILK':2}
        if case==1: own['private']['shed']['WHEAT']=5
        if case==2: own['private']['shed']['FERTILIZER']=98
        if case==3:
            own['market']['inventory']['WHEAT']=1000000
            game._refresh_prices(own['market'])
        rival={**deepcopy(own),'player':1,'private':game._new_private()}
        rival_action={'farmer':['PASS'],'hands':[],'market':[]}
        if case==4:
            rival['private']['shed']['WHEAT']=4
            rival_action['market']=[['SELL','WHEAT',4]]
        control={'farmer':['DROP'],'hands':[],'market':[['SELL','WHEAT',5]] if case==1 else []}
        post=apply_farm_actions(own,control,game)
        aligned={**deepcopy(control),'market':terminal_market_rule(post,game,fertilizer_value)}
        f=extract_cash_features(own,post['private'],control['market'],aligned['market'],game.PRODUCTS,game.market_price)
        a=isolated_transition(own,rival,control,rival_action,game)
        b=isolated_transition(own,rival,aligned,rival_action,game)
        effect=effects(own,a,b,game.PRODUCTS)
        if case!=4 and not math.isclose(f.values['cash.solo_revenue_delta'],effect['own_cash_delta'],abs_tol=1e-8):
            raise ValueError('No-rival scenario fails exact interpreter parity')
        if case==0 and (a[0]['status']!='DONE' or b[0]['status']!='DONE'):
            raise ValueError('Final-callback fixture did not terminate')
        rows.append({'case':case,'kind':'synthetic_engine_fixture','passed':True,
                     'solo_scenario_delta':f.values['cash.solo_revenue_delta'],**effect})
        write(OUT/'mechanics.json',rows)
    return rows


def replay(root,game,fp):
    from callback import CashPolicy
    from cash_features import non_sell_orders
    from kaggriculture_research.artifacts import load_checkpoint
    from kaggriculture_staffing.experiment import validate_episode
    progress=read(root/'reports/staffing_progress.json')
    artifacts=progress['artifact_manifest']
    if progress['completed_games']!=7 or progress['complete'] or len(artifacts)!=7:
        raise ValueError('Unexpected frozen pilot scope')
    if len({a['path'] for a in artifacts})!=7: raise ValueError('Duplicate artifacts')
    output=[]
    for index,a in enumerate(artifacts,1):
        key={k:a[k] for k in ('seed','seat','opponent','arm')};ident=digest(key)[:20]
        p=contained(root,a['path'])
        if sha(p)!=a['sha256']: raise ValueError('Episode source hash changed')
        episode_fp=digest({'run':fp,'key':key,'source':a['sha256']})
        cache=OUT/'checkpoints'/f'episode-{ident}.json.gz'
        prior=load_cache(cache,episode_fp)
        if prior is not None:
            runtime_gate(prior['checks']);output.append(prior)
            log('EPISODE_REUSED',episode=index,total=7);continue
        payload=load_checkpoint(p,{**progress['lineage'],**key})
        if payload is None: raise ValueError('Frozen checkpoint lineage mismatch')
        validate_episode(payload,key)
        records={}
        for record in payload['records']:
            o=record['observation'];slot=(o['day']*24+o['hour'],record['player'])
            if slot in records: raise ValueError('Duplicate recorded callback')
            records[slot]=record
        early=[]
        for step in (0,24,695):
            row=records[(step,key['seat'])]
            for arm in ('control','aligned'):
                actor=CashPolicy(key['arm'],arm)
                actor.prime_recorded_clock(None if step==0 else step-1,key['seat'])
                action=actor(deepcopy(row['observation']))
                if action!=row['action']: raise ValueError('Pre-terminal source action parity failed')
            early.append({'step':step,'passed':True})
        actors={arm:CashPolicy(key['arm'],arm) for arm in ('control','aligned')}
        for actor in actors.values(): actor.prime_recorded_clock(695,key['seat'])
        state_rows=[];product_rows=[];checks=[];outcomes=[]
        for step in range(696,719):
            row=records[(step,key['seat'])];rival=records[(step,1-key['seat'])]
            obs=row['observation'];unchanged=deepcopy(obs)
            meta={**key,'source_arm':key['arm'],'episode_id':ident,'step':step}
            actions={};elapsed={};diagnostics={}
            order=('control','aligned') if step%2==0 else ('aligned','control')
            for arm in order:
                tick=time.perf_counter();actions[arm]=actors[arm](obs)
                elapsed[arm]=(time.perf_counter()-tick)*1000
                diagnostics[arm]=deepcopy(actors[arm].last_diagnostics)
            check={**meta,**{arm+'_callback_ms':elapsed[arm] for arm in elapsed},
                   'recorded_control_action_parity':actions['control']==row['action'],
                   'farm_action_parity':all(actions['control'][k]==actions['aligned'][k] for k in ('farmer','hands')),
                   'non_sell_parity':non_sell_orders(actions['control'])==non_sell_orders(actions['aligned']),
                   'input_unchanged':obs==unchanged,
                   'base_rule_parity':all(diagnostics[arm]['base_rule_parity'] for arm in diagnostics),
                   'market_changed':actions['control']['market']!=actions['aligned']['market']}
            checks.append(check)
            # Save the actual sample and commands BEFORE gating; no failed tail erased.
            write(OUT/'latest_callback.json',{'sample':check,'actions':actions,'observation_sha256':digest(obs)})
            if not all(check[k] for k in ('recorded_control_action_parity','farm_action_parity','non_sell_parity','input_unchanged','base_rule_parity')):
                raise ValueError('Callback attribution/parity failed; see latest_callback.json')
            runtime_gate([check])
            d=diagnostics['aligned']
            state_rows.append({**meta,**d['features']})
            product_rows.extend({**meta,**r} for r in d['products'])
            c=isolated_transition(obs,rival['observation'],actions['control'],rival['action'],game)
            n=isolated_transition(obs,rival['observation'],actions['aligned'],rival['action'],game)
            next_records={seat:records[(step+1,seat)] for seat in (0,1)} if step<718 else None
            assert_source_transition(c,next_records,payload['rewards'],step)
            outcomes.append({**meta,'recorded_transition_parity':True,
                'scope':'one_step_saved_state_fixed_rival_action','final_callback':step==718,
                **effects(obs,c,n,game.PRODUCTS)})
        data={'key':key,'early_parity':early,'checks':checks,'states':state_rows,
              'products':product_rows,'effects':outcomes}
        save_cache(cache,episode_fp,data);output.append(data)
        log('EPISODE_CHECKPOINT_SAVED',episode=index,total=7,observations=len(checks),
            market_changes=sum(r['market_changed'] for r in checks),
            max_callback_ms=max(max(r['control_callback_ms'],r['aligned_callback_ms']) for r in checks))
    return output


def summarize(episodes,mechanics_rows,pf,tests,fp,started):
    import pandas as pd
    from cash_features import SCHEMA
    states=pd.DataFrame([r for e in episodes for r in e['states']])
    products=pd.DataFrame([r for e in episodes for r in e['products']])
    checks=pd.DataFrame([r for e in episodes for r in e['checks']])
    outcomes=pd.DataFrame([r for e in episodes for r in e['effects']])
    features=[c for c in states if c.startswith('cash.')]
    if len(states)!=161 or len(features)!=158 or len(episodes)!=7: raise ValueError('Unexpected evidence/schema scope')
    group=outcomes.groupby(['seed','seat','opponent','source_arm','episode_id'],dropna=False)
    grouped=group.agg(observations=('step','size'),positive_one_step_states=('own_cash_delta',lambda x:int((x>0).sum())),
        negative_one_step_states=('own_cash_delta',lambda x:int((x<0).sum())),
        mean_one_step_cash_delta=('own_cash_delta','mean'),max_one_step_cash_delta=('own_cash_delta','max'),
        min_one_step_cash_delta=('own_cash_delta','min')).reset_index()
    registry=pd.DataFrame([{'feature':c,'distinct_values':int(states[c].nunique()),
        'minimum':float(states[c].min()),'maximum':float(states[c].max()),
        'nonzero_fraction':float((states[c]!=0).mean()),
        'status':'causal_candidate_not_competition_validated'} for c in features])
    exports={'state_features.csv':states,'product_features.csv':products,'callback_checks.csv':checks,
             'one_step_effects.csv':outcomes,'effects_by_episode.csv':grouped,
             'feature_registry.csv':registry}
    for name,frame in exports.items(): write_bytes(OUT/name,frame.to_csv(index=False).encode())
    changed=int(checks.market_changed.sum());negative=int((outcomes.own_cash_delta<0).sum())
    decision=('STOP_NO_ACTIVATION' if not changed else
              'REVIEW_NEGATIVE_ONE_STEP_STATES' if negative else 'ACTIVATED_REQUIRES_PAIRED_CONTINUATION')
    r={'status':STATUS,'utc':utc(),'schema':SCHEMA,'source_commit':COMMIT,'code_sha256':code_hash(),
       'engine_sha256':ENGINE,'fingerprint':fp,'execution_mode':'AWS_SAVED_OBSERVATIONS',
       'source_episodes':7,'saved_observations':161,'source_seed_blocks':2,
       'candidate_descriptors':len(features),'varying_descriptors':int((registry.distinct_values>1).sum()),
       'market_action_changes':changed,'negative_one_step_states':negative,
       'positive_one_step_states':int((outcomes.own_cash_delta>0).sum()),
       'complete_terminal_callback_gate':'PASSED_ON_REPLAYED_STATES',
       'callback_limit_ms':CALLBACK_LIMIT_MS,
       'callback_ms':{arm:{'median':float(checks[arm+'_callback_ms'].median()),
                           'p95':float(checks[arm+'_callback_ms'].quantile(.95)),
                           'max':float(checks[arm+'_callback_ms'].max())} for arm in ('control','aligned')},
       'all_control_actions_match_recorded':bool(checks.recorded_control_action_parity.all()),
       'same_farm_actions_all_states':bool(checks.farm_action_parity.all()),
       'same_non_sell_orders_all_states':bool(checks.non_sell_parity.all()),
       'recorded_interpreter_transition_parity_checks':161,
       'pre_terminal_action_parity_states':sum(len(e['early_parity']) for e in episodes),
       'synthetic_engine_fixtures':len(mechanics_rows),'interpreter_calls':322+2*len(mechanics_rows),
       'decision':decision,'one_step_cash_delta_min':float(outcomes.own_cash_delta.min()),
       'one_step_cash_delta_max':float(outcomes.own_cash_delta.max()),
       'official_submission_score':None,'official_metric_effect_measured':False,
       'complete_game_gain_measured':False,'feature_value_proven':False,'new_complete_games':0,
       'models_fit':0,'validation_or_holdout_used':False,'github_updated':False,'aws_resources_modified':False,
       'frozen_sources_modified':False,'feature_completion_gate':'OPEN','tests':tests,
       'elapsed_seconds':time.monotonic()-started,
       'timing_scope':'Entire new terminal __call__, including common base, routing, post-action simulation, features and diagnostics. Excludes harness I/O/evaluator; not hosted Kaggle timing. Cache hits retain original timings.',
       'limitations':['Frozen seven-game development slice; eighth game was latency-censored; two seed blocks, one opponent.',
         'Each intervention is a separate one-step branch. Do not sum turn deltas into a season gain.',
         'Recorded rival action fixed for each counterfactual; no evidence about adaptive opponent response.',
         'Frozen callback still admits at most three hired hands on either farm. Broader-workforce extractor coverage does not certify this callback.',
         'One-step evaluator sees both saved private states, but policies/features receive only their own legal observation.',
         'Source already contains deadline, water-then-harvest, fertilizer collection and two-collection routes; these are not claimed as newly invented here.'],
       'output_sha256':{name:sha(OUT/name) for name in exports}}
    write(OUT/'report.json',r);log(STATUS,decision=decision,market_action_changes=changed)
    return r


def worker(args):
    started=time.monotonic();tests=run_tests();root,game,pf=preflight(args)
    fp=digest({'code':code_hash(),'source':COMMIT,'engine':ENGINE,
               'prior_report':pf['prior_report_sha256'],'progress':sha(root/'reports/staffing_progress.json')})
    mechanics_rows=mechanics(game);log('MECHANICS_PASSED',fixtures=len(mechanics_rows))
    episodes=replay(root,game,fp)
    summarize(episodes,mechanics_rows,pf,tests,fp,started)


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
                raise TimeoutError('180-second maximum work budget reached; saved episode checkpoints preserved')
            if now-last>=10: log('HEARTBEAT',elapsed_seconds=round(now-start,1));last=now
            time.sleep(.1)
    except BaseException:
        if child.poll() is None: os.killpg(child.pid,signal.SIGKILL);child.wait()
        raise
    if child.returncode: raise RuntimeError('Worker failed; inspect saved failure_worker.json')


def verify():
    r=read(OUT/'report.json');s=read(OUT/'run_status.json')
    if r['status']!=STATUS or r['code_sha256']!=code_hash(): raise ValueError('Status/code differs')
    if s['status']!='PASSED' or s['report_sha256']!=sha(OUT/'report.json'): raise ValueError('No matching pass receipt')
    for rel,h in r['output_sha256'].items():
        if sha(contained(OUT,rel))!=h: raise ValueError('Output hash mismatch '+rel)
    return r


def run(args):
    import fcntl
    OUT.mkdir(exist_ok=True)
    with (OUT/'.run.lock').open('a+') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('Another notebook08 process is active')
        if (OUT/'run_status.json').exists():
            previous=read(OUT/'run_status.json')
            if previous['status']=='PASSED': preflight(args);verify();log('EXISTING_PASS_REUSED');return
            if not args.resume_after_review: raise RuntimeError('Earlier attempt needs diagnosis; no unchanged automatic retries')
        write(OUT/'run_status.json',{'status':'RUNNING','utc':utc()})
        try:
            supervise([sys.executable,str(BASE/'run_cash.py'),'_worker','--previous',str(args.previous),
                       '--resume',str(args.resume)],args.seconds)
            r=read(OUT/'report.json')
            if r['status']!=STATUS: raise ValueError('No successful worker report')
            write(OUT/'run_status.json',{'status':'PASSED','utc':utc(),'report_sha256':sha(OUT/'report.json')})
            verify();log('NOTEBOOK08_COMPLETE')
        except BaseException:
            write(OUT/'run_status.json',{'status':'FAILED','utc':utc()})
            raise


def bundle():
    OUT.mkdir(exist_ok=True)
    allowed=('report.json','run_status.json','tests.json','preflight.json','mechanics.json',
             'latest_callback.json','events.jsonl','failure.json','failure_worker.json',
             'state_features.csv','product_features.csv','callback_checks.csv','one_step_effects.csv',
             'effects_by_episode.csv','feature_registry.csv','cash_realization.html')
    paths=[(OUT/n,'outputs/'+n) for n in allowed if (OUT/n).is_file() and not (OUT/n).is_symlink()]
    paths += [(p,'outputs/checkpoints/'+p.name) for p in sorted((OUT/'checkpoints').glob('episode-*.json.gz')) if not p.is_symlink()]
    paths += [(BASE/'08_post_action_cash_features.ipynb','08_post_action_cash_features.ipynb')]
    paths += [(BASE/'reference/input_review.json','reference/input_review.json')]
    paths=[(p,n) for p,n in paths if p.is_file()]
    dest=BASE/'kaggriculture_cash_realization_results.zip';tmp=dest.with_suffix('.tmp')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for p,n in paths:z.write(p,n)
        z.writestr('BUNDLE_MANIFEST.json',json.dumps({'utc':utc(),'files':{n:sha(p) for p,n in paths},
            'raw_input_episodes_included':False,'credentials_included':False},indent=2))
    os.replace(tmp,dest);print('UPLOAD THIS RESULTS FILE:',dest,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['run','_worker','verify','bundle','tests'])
    parser.add_argument('--previous',type=Path,default=PREVIOUS)
    parser.add_argument('--resume',type=Path,default=RESUME)
    parser.add_argument('--seconds',type=int,default=180)
    parser.add_argument('--resume-after-review',action='store_true')
    args=parser.parse_args()
    if not 30<=args.seconds<=180:parser.error('Budget must be 30..180 seconds')
    try:
        if args.stage=='run':run(args)
        elif args.stage=='_worker':worker(args)
        elif args.stage=='verify':print(json.dumps(verify(),indent=2))
        elif args.stage=='tests':run_tests()
        else:bundle()
    except BaseException as exc:
        if args.stage!='bundle':
            write(OUT/('failure_worker.json' if args.stage=='_worker' else 'failure.json'),{
                'utc':utc(),'stage':args.stage,'type':type(exc).__name__,'error':str(exc),
                'traceback':traceback.format_exc(),'checkpoints_preserved':True})
        raise

if __name__=='__main__':main()
