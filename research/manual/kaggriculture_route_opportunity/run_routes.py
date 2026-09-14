"""Bounded local stages. No installs, new seasons, network, AWS or Git writes."""
from __future__ import annotations
import argparse,gzip,importlib,json,math,os,signal,subprocess,sys,tempfile,time,traceback,unittest,zipfile
from pathlib import Path
from copy import deepcopy
from route_io import utc,read,sha,inside,write,atomic,digest,code_hash,save_cache,load_cache

BASE=Path(__file__).resolve().parent
OUT=BASE/'outputs'
COMMIT='7194116dfc92a8663139611233b5a221dad431a4'
ENGINE='bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e'
CAPS={'screen':90,'pilot':120}
KEYS=('seed','seat','opponent','arm')


def log(stage,**kw):
    OUT.mkdir(exist_ok=True);row={'utc':utc(),'stage':stage,**kw}
    with (OUT/'events.jsonl').open('a') as f:f.write(json.dumps(row,allow_nan=False)+'\n');f.flush()
    print(json.dumps(row,allow_nan=False),flush=True)

def emit(event,row):
    write(OUT/'latest_measurement.json',{'event':event,**row})
    with (OUT/'callback_trace.jsonl').open('a') as f:
        f.write(json.dumps({'utc':utc(),'event':event,**row},allow_nan=False)+'\n');f.flush()

def verify_package():
    for rel,h in read(BASE/'PACKAGE_MANIFEST.json')['files'].items():
        if sha(inside(BASE,rel))!=h:raise ValueError('Package file differs: '+rel)

def prior_check(home):
    previous=home/'kaggriculture_sale_timing'
    r=read(previous/'outputs/report.json');s=read(previous/'outputs/run_status.json')
    review=read(BASE/'reference/input_review.json')
    if sha(previous/'outputs/report.json')!=review['report_sha256'] or s['status']!='COMPLETED' or s['report_sha256']!=review['report_sha256']:
        raise ValueError('Notebook10 result differs from reviewed completed result')
    if r['code_sha256']!=code_hash(previous):raise ValueError('Notebook10 source changed')
    for n,h in r['output_sha256'].items():
        if sha(inside(previous/'outputs',n))!=h:raise ValueError('Notebook10 output changed: '+n)
    if r['completed_pairs']!=7 or r['decision']!='PROMISING_DEVELOPMENT_ONLY_FRESH_VALIDATION_REQUIRED':
        raise ValueError('Wrong prerequisite result')
    for folder,items in read(BASE/'reference/dependency_hashes.json').items():
        for rel,h in items.items():
            if sha(inside(home/folder,rel))!=h:raise ValueError('Dependency changed: '+folder+'/'+rel)
    return r


def import_at(name,folder):
    sys.path.insert(0,str(folder));module=importlib.import_module(name)
    if Path(module.__file__).resolve()!=(folder/(name+'.py')).resolve():raise ValueError('Wrong import: '+name)
    return module


def preflight(home):
    verify_package();prior=prior_check(home)
    resume=home/'kaggriculture_manual_resume'
    source=read(resume/'state/source.json');runtime=read(resume/'state/runtime.json')
    restore=read(resume/'state/restore.json');ready=read(resume/'state/readiness.json')
    if any(x.get('status')!='PASSED' for x in (source,runtime,restore)):raise ValueError('Readiness receipts not passed')
    if sys.version_info[:2]!=(3,12) or Path(sys.executable).absolute()!=Path(runtime['executable']).absolute():
        raise ValueError('Select the verified manual kernel; do not reinstall')
    repo=Path(source['repo']).resolve()
    def git(*args):return subprocess.check_output(['git',*args],cwd=repo,text=True,timeout=10).strip()
    if git('rev-parse','HEAD')!=COMMIT or git('status','--porcelain','--untracked-files=no'):
        raise ValueError('Checkout changed; preserve work, do not reset')
    for rel,h in ready['source_files'].items():
        if sha(inside(repo,rel))!=h:raise ValueError('Reviewed source changed: '+rel)
    sys.path.insert(0,str(repo/'src'))
    from kaggriculture_research import environment
    if not Path(environment.__file__).resolve().is_relative_to(repo/'src'):raise ValueError('Wrong source imports')
    if environment.engine_manifest()['files']['envs/kaggriculture/kaggriculture.py']!=ENGINE:raise ValueError('Wrong engine')
    root=Path(restore['private_root']).resolve()
    if restore['episode_count']!=7 or len(restore['downloaded_or_reused'])!=10:raise ValueError('Recovery scope differs')
    for obj in restore['downloaded_or_reused']:
        p=inside(root,obj['path'])
        if p.stat().st_size!=obj['bytes'] or sha(p)!=obj['sha256']:raise ValueError('Recovered data changed')
    mods={n:import_at(n,home/'kaggriculture_cash_realization') for n in ('cash_features','callback','run_cash')}
    mods['continuation']=import_at('continuation',home/'kaggriculture_terminal_ablation')
    mods['timing_features']=import_at('timing_features',home/'kaggriculture_sale_timing')
    fp=digest({'code':code_hash(BASE),'protocol':sha(BASE/'PROTOCOL.json'),'engine':ENGINE,
               'previous':sha(home/'kaggriculture_sale_timing/outputs/report.json'),
               'source':COMMIT,'progress':sha(root/'reports/staffing_progress.json')})
    pf={'status':'PASSED','utc':utc(),'source_commit':COMMIT,'engine_sha256':ENGINE,'verified_objects':10,
        'repo':str(repo),'private_root':str(root),'fingerprint':fp}
    write(OUT/'preflight.json',pf);log('PREFLIGHT_PASSED',verified_objects=10)
    return root,environment.game,mods,fp


def source_jobs(root):
    progress=read(root/'reports/staffing_progress.json')
    jobs=sorted(progress['artifact_manifest'],key=lambda a:(a['seed'],a['seat'],a['arm']))
    expected={(1601,0,'coordinated'),(1601,1,'coordinated'),(1602,0,'coordinated'),
              (1601,0,'sequential'),(1601,1,'sequential'),(1602,0,'sequential'),(1602,1,'sequential')}
    if len(jobs)!=7 or {(a['seed'],a['seat'],a['arm']) for a in jobs}!=expected:raise ValueError('Source scope differs')
    return progress,jobs


def load_source(root,progress,job):
    from kaggriculture_research.artifacts import load_checkpoint
    from kaggriculture_staffing.experiment import validate_episode
    p=inside(root,job['path']);key={k:job[k] for k in KEYS}
    if sha(p)!=job['sha256']:raise ValueError('Source file mismatch')
    payload=load_checkpoint(p,{**progress['lineage'],**key})
    if payload is None:raise ValueError('Source lineage mismatch')
    validate_episode(payload,key)
    return payload,key


def test_stage():
    suite=unittest.defaultTestLoader.discover(str(BASE/'tests'))
    result=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
    report={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)}
    write(OUT/'tests.json',report)
    if not result.wasSuccessful() or result.skipped:raise RuntimeError('Unit tests failed/skipped')
    return report


def save_csv(path,rows):
    import pandas as pd
    data=pd.DataFrame(rows).to_csv(index=False).encode()
    atomic(path,gzip.compress(data,mtime=0) if str(path).endswith('.gz') else data)


def report_common(fp):
    return {'utc':utc(),'fingerprint':fp,'code_sha256':code_hash(BASE),'source_commit':COMMIT,
            'engine_sha256':ENGINE,'official_submission_score':None,'official_metric_effect_measured':False,
            'new_complete_games':0,'models_fit':0,'github_updated':False,'cloud_resources_modified':False,
            'feature_engineering_complete':False}


def screen(home):
    started=time.monotonic();tests=test_stage();root,game,mods,fp=preflight(home)
    from route_policy import RouteOpportunityPolicy
    from route_features import FIELDS
    from route_experiment import measure
    from kaggriculture_terminal import routing
    cont=mods['continuation']; progress,jobs=source_jobs(root)
    selected=[j for j in jobs if j['arm']=='coordinated'];done=[]
    for job in selected:
        key={k:job[k] for k in KEYS};ident=digest(key)[:20]
        p=OUT/'screen/checkpoints'/(ident+'.json.gz');cpf=digest({'run':fp,'stage':'screen','source':job['sha256']})
        cached=load_cache(p,cpf)
        if cached is None:
            payload,key=load_source(root,progress,job);records=cont.index_episode(payload)
            actor=RouteOpportunityPolicy('coordinated','opportunity');actor.prime_recorded_clock(695,key['seat'])
            ref=mods['timing_features'].FinalSalePolicy('coordinated');ref.prime_recorded_clock(695,key['seat'])
            states=[];features=[]
            for step in range(696,719):
                obs=cont.legal_observation(records[(step,key['seat'])]['observation'])
                action,ms=measure(actor,obs,'screen_candidate',emit)
                control,rms=measure(ref,obs,'screen_reference',emit)
                frozen,meta=routing.menus(obs)
                if frozen!=actor.original_menus or meta!=actor.route_meta:
                    raise ValueError('New candidate enumerator differs from frozen routing.menus')
                if control!=actor.last_diagnostics['same_state_control_action']:
                    raise ValueError('Reference callback parity failed')
                d=actor.last_diagnostics['routing']
                states.append({**key,'step':step,'candidate_callback_ms':ms,'reference_callback_ms':rms,
                    **{k:v for k,v in d.items() if k not in ('baseline_commands','chosen_commands')},
                    'menu_generation_parity':True,'reference_action_parity':True})
                features.extend({**key,'step':step,**row} for row in actor.route_rows)
            cached={'key':key,'states':states,'routes':features}
            save_cache(p,cpf,cached);log('SCREEN_EPISODE_SAVED',**key,states=23)
        else:log('SCREEN_EPISODE_REUSED',**key)
        done.append(cached)
    states=[r for d in done for r in d['states']];features=[r for d in done for r in d['routes']]
    if len(states)!=69 or not all(r['menu_generation_parity'] for r in states):raise ValueError('Incomplete screen')
    activated=[d['key'] for d in done if any(s['farm_commands_changed'] for s in d['states'])]
    chosen=activated[0] if activated else None # fixed lexicographic order, not best observed outcome
    save_csv(OUT/'screen/states.csv',states);save_csv(OUT/'screen/route_candidates.csv.gz',features)
    registry=[]
    for field in FIELDS:
        vals=[r['route.'+field] for r in features]
        registry.append({'feature':'route.'+field,'distinct_values':len(set(vals)),
                         'min':min(vals,default=0),'max':max(vals,default=0),
                         'nonzero_fraction':sum(v!=0 for v in vals)/max(1,len(vals)),
                         'status':'activation_only_not_predictive_importance'})
    save_csv(OUT/'screen/feature_registry.csv',registry)
    report={**report_common(fp),'status':'ROUTE_OPPORTUNITY_SCREEN_COMPLETE',
            'decision':'ELIGIBLE_FOR_ONE_PAIRED_PILOT' if chosen else 'STOP_NO_ACTION_ACTIVATION',
            'selected_key':chosen,'observations':len(states),'source_episodes':3,
            'route_rows':len(features),'numeric_descriptors_per_route':len(FIELDS),'tests':tests,
            'changed_first_command_states':sum(r['farm_commands_changed'] for r in states),
            'static_objective_improved_states':sum(r['static_key_improved'] for r in states),
            'candidate_callback_max_ms':max(r['candidate_callback_ms'] for r in states),
            'elapsed_seconds':time.monotonic()-started,
            'output_sha256':{n:sha(OUT/n) for n in ('screen/states.csv','screen/route_candidates.csv.gz','screen/feature_registry.csv')},
            'limitations':['Same two previously examined development seeds; no validation or holdout used.',
               'Static utility is current-price, no-opponent, at-most-two-collections scenario, not realized cash.',
               'Reference-menu opportunity losses are independent-worker pressure approximations.',
               'Eight non-PASS routes per worker; <=3 hands per farm inherited callback restriction.',
               'Selected first activated source by lexicographic identity; this is training-slice screening, not independent validation.']}
    write(OUT/'screen/report.json',report);log(report['status'],decision=report['decision'],changed_states=report['changed_first_command_states'])


def verify_stage(stage):
    r=read(OUT/stage/'report.json');s=read(OUT/stage/'status.json')
    if s['status']!='COMPLETED' or s['report_sha256']!=sha(OUT/stage/'report.json') or r['code_sha256']!=code_hash(BASE):
        raise ValueError('Stage completion/code mismatch')
    for rel,h in r.get('output_sha256',{}).items():
        if sha(inside(OUT,rel))!=h:raise ValueError('Stage output changed')
    return r


def pilot(home):
    started=time.monotonic();root,game,mods,fp=preflight(home);s=verify_stage('screen')
    if s['fingerprint']!=fp:raise ValueError('Screen lineage differs')
    from route_experiment import rollout,paired,decision
    if s['selected_key'] is None:
        report={**report_common(fp),'status':'ROUTE_OPPORTUNITY_PILOT_COMPLETE',
                'decision':'STOP_NO_ACTION_ACTIVATION','completed_pairs':0,'interpreter_transitions':0,
                'output_sha256':{},'elapsed_seconds':time.monotonic()-started}
        write(OUT/'pilot/report.json',report);log(report['status'],decision=report['decision']);return
    progress,jobs=source_jobs(root)
    negative=next(j for j in jobs if (j['seed'],j['seat'],j['arm'])==(1601,0,'sequential'))
    primary=next(j for j in jobs if {k:j[k] for k in KEYS}==s['selected_key'])
    import pandas as pd
    prior=pd.read_csv(home/'kaggriculture_sale_timing/outputs/final_comparisons.csv').to_dict('records')
    pairs=[];all_branches=[];new_calls=0
    for job in (negative,primary):
        payload,key=load_source(root,progress,job);expected=next(r for r in prior if all(r[k]==key[k] for k in KEYS))
        branches=[]
        for mode in ('control','opportunity'):
            ident=digest(key)[:20];p=OUT/'pilot/checkpoints'/f'{ident}-{mode}.json.gz'
            cpf=digest({'run':fp,'stage':'pilot','source':job['sha256'],'mode':mode})
            branch=load_cache(p,cpf)
            if branch is None:
                branch=rollout(payload,key,mode,game,mods,emit,expected)
                save_cache(p,cpf,branch);new_calls+=23;log('BRANCH_CHECKPOINT_SAVED',mode=mode,**key)
            else:log('BRANCH_REUSED',mode=mode,**key)
            if branch['transitions']!=23:raise ValueError('Partial branch checkpoint')
            branches.append(branch);all_branches.append(branch)
        row=paired(*branches);pairs.append(row)
        save_csv(OUT/'pilot/paired_results.csv',pairs);write(OUT/'pilot/progress.json',{'pairs':pairs})
        log('PAIR_COMPLETE',**key,coins_delta=row['coins_delta'],match_delta=row['local_match_score_delta'])
        if row['role']=='primary':break # hard one-primary-pair budget; no scale-up
    save_csv(OUT/'pilot/trajectories.csv',[{**b['key'],**t} for b in all_branches for t in b['trace']])
    report={**report_common(fp),'status':'ROUTE_OPPORTUNITY_PILOT_COMPLETE','decision':decision(pairs),
            'completed_pairs':len(pairs),'primary_pairs':1,'negative_controls':1,'paired_results':pairs,
            'interpreter_transitions':new_calls,'represented_transitions':sum(b['transitions'] for b in all_branches),
            'candidate_callback_max_ms':max(t['candidate_callback_ms'] for b in all_branches for t in b['trace']),
            'elapsed_seconds':time.monotonic()-started,
            'output_sha256':{n:sha(OUT/n) for n in ('pilot/paired_results.csv','pilot/trajectories.csv')},
            'limitations':['One activation-selected primary source and one no-change control; development-only.',
                'Responsive opponent is one related livestock_fertilizer policy; not a competitive league.',
                'Control reproduces notebook10 endpoints and the original prefix; final-sale rule is shared.',
                'No earlier season decisions changed; income from new production/land/hiring not tested.',
                'Policy still rejects >3 hired hands on either farm; not a submission-ready broad-workforce agent.',
                'Local checkpoints have hashes/readback; no automatic S3 or GitHub writes.']}
    write(OUT/'pilot/report.json',report);log(report['status'],decision=report['decision'])


def supervise(stage,home):
    path=OUT/stage/'status.json'
    if path.exists():
        s=read(path)
        if s['status']=='COMPLETED':
            r=verify_stage(stage);prior_check(home);log('VERIFIED_STAGE_REUSED',name=stage,decision=r['decision']);return
        raise RuntimeError('Prior stage active/failed/interrupted. Bundle evidence; no unchanged retry.')
    write(path,{'status':'RUNNING','utc':utc()})
    child=subprocess.Popen([sys.executable,str(BASE/'run_routes.py'),'_'+stage,'--home',str(home)],start_new_session=True)
    t=time.monotonic();beat=t
    try:
        while child.poll() is None:
            now=time.monotonic()
            if now-t>CAPS[stage]:raise TimeoutError(str(CAPS[stage])+' second stage cap reached')
            if now-beat>=10:log('HEARTBEAT',name=stage,elapsed_seconds=round(now-t,1));beat=now
            time.sleep(.2)
        if child.returncode:raise RuntimeError('Stage failed; bundle diagnostics without retry')
        write(path,{'status':'COMPLETED','utc':utc(),'report_sha256':sha(OUT/stage/'report.json')})
    except BaseException:
        if child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=2)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        write(path,{'status':'FAILED','utc':utc()});raise


def bundle():
    paths=[p for p in OUT.rglob('*') if p.is_file() and not p.is_symlink() and p.suffix in ('.json','.jsonl','.csv','.gz','.html','.txt')]
    paths += [BASE/n for n in ('11_route_opportunity_feature_ablation.ipynb','PROTOCOL.json','FEATURE_RESEARCH.md','LOCAL_VALIDATION.json','reference/input_review.json')]
    paths=[p for p in paths if p.exists()]
    if any(p.stat().st_size>50_000_000 for p in paths):raise ValueError('Unexpectedly large output')
    m={'utc':utc(),'files':{str(p.relative_to(BASE)):sha(p) for p in paths}}
    dest=BASE/'kaggriculture_route_opportunity_results.zip';fd,tmp=tempfile.mkstemp(prefix='.bundle-',dir=BASE);os.close(fd)
    try:
        with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
            for p in paths:z.write(p,str(p.relative_to(BASE)))
            z.writestr('BUNDLE_MANIFEST.json',json.dumps(m,indent=2))
        os.replace(tmp,dest)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    print('RESULTS_BUNDLE:',dest,flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['screen','pilot','_screen','_pilot','bundle','tests'])
    ap.add_argument('--home',type=Path,default=Path.home());a=ap.parse_args()
    try:
        if a.command=='bundle':bundle()
        elif a.command=='tests':test_stage()
        elif a.command.startswith('_'):{'_screen':screen,'_pilot':pilot}[a.command](a.home)
        else:supervise(a.command,a.home)
    except BaseException as e:
        write(OUT/('failure_'+a.command+'.json'),{'utc':utc(),'command':a.command,'error':str(e),'traceback':traceback.format_exc()});raise

if __name__=='__main__':
    def stop(sig,frame):raise KeyboardInterrupt('Stop requested; checkpoints preserved')
    signal.signal(signal.SIGTERM,stop)
    main()
