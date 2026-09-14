"""Two bounded manual stages; no installs, network requests, or cloud/Git writes."""
from __future__ import annotations
import argparse, gzip, importlib, json, os, signal, subprocess, sys, tempfile, time, traceback, unittest, zipfile
from pathlib import Path
from copy import deepcopy
from research_io import read, sha, inside, write, atomic, digest, code_hash, save_cache, load_cache, utc
BASE = Path(__file__).resolve().parent
OUT = BASE / 'outputs'
COMMIT = '7194116dfc92a8663139611233b5a221dad431a4'
ENGINE = 'bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e'
CAPS = {'screen': 90, 'pilot': 180}
KEYS = ('seed', 'seat', 'opponent', 'arm')

def log(stage, **kwargs):
    OUT.mkdir(exist_ok=True)
    row = {'utc': utc(), 'stage': stage, **kwargs}
    with (OUT / 'events.jsonl').open('a') as f:
        f.write(json.dumps(row, allow_nan=False) + '\n')
        f.flush()
    print(json.dumps(row, allow_nan=False), flush=True)

def emit(event, row):
    write(OUT / 'latest_measurement.json', {'event': event, **row})
    with (OUT / 'callback_trace.jsonl').open('a') as f:
        f.write(json.dumps({'utc': utc(), 'event': event, **row}, allow_nan=False) + '\n')
        f.flush()

def verify_package():
    manifest=read(BASE/'PACKAGE_MANIFEST.json')
    for name,h in manifest['files'].items():
        if sha(inside(BASE,name))!=h:raise ValueError('Package file changed: '+name)
    nb=read(BASE/'14_harvest_value_feature_ablation.ipynb')
    body=[{'cell_type':c['cell_type'],'source':''.join(c['source']) if isinstance(c['source'],list) else c['source']} for c in nb['cells']]
    if digest(body)!=manifest['notebook_source_sha256']:raise ValueError('Notebook source changed; saved outputs are allowed')

def prior_check(home):
    previous=home/'kaggriculture_maintenance_diagnosis'
    hashes=read(BASE/'reference/input_hashes.json')['files']
    for rel,h in hashes.items():
        if rel.endswith('.ipynb') or rel in ('LOCAL_VALIDATION.json','PROTOCOL.json'): continue
        if sha(inside(previous,rel))!=h: raise ValueError('Notebook13 artifact differs: '+rel)
    r=read(previous/'outputs/report.json');s=read(previous/'outputs/status.json')
    if s.get('status')!='COMPLETED' or s.get('report_sha256')!=sha(previous/'outputs/report.json') or r['code_sha256']!=code_hash(previous):
        raise ValueError('Notebook13 completed report or source differs')
    if r['decision']!='DIAGNOSIS_ONLY_NO_POLICY_PROMOTION' or r['cash_delta_reconciled']!=-396 or not r['all_turn_cash_and_final_state_checks_passed']:
        raise ValueError('Different diagnosis; do not run an unchanged hypothesis')
    for folder,items in read(BASE/'reference/dependency_hashes.json').items():
        for rel,h in items.items():
            if sha(inside(home/folder,rel))!=h:raise ValueError('Dependency changed: '+folder+'/'+rel)
    return r

def preflight(home):
    verify_package()
    prior = prior_check(home)
    old = home / 'kaggriculture_manual_resume'
    source = read(old / 'state/source.json')
    runtime = read(old / 'state/runtime.json')
    restore = read(old / 'state/restore.json')
    ready = read(old / 'state/readiness.json')
    if any((r.get('status') != 'PASSED' for r in (source, runtime, restore))):
        raise ValueError('Earlier readiness incomplete')
    if sys.version_info[:2] != (3, 12) or Path(sys.executable).absolute() != Path(runtime['executable']).absolute():
        raise ValueError('Use Kaggriculture Manual (verified source); do not reinstall')
    repo = Path(source['repo']).resolve()

    def git(*args):
        return subprocess.check_output(['git', *args], cwd=repo, text=True, timeout=10).strip()
    if git('rev-parse', 'HEAD') != COMMIT or git('status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Reviewed checkout changed; preserve it, do not reset')
    for rel, h in ready['source_files'].items():
        if sha(inside(repo, rel)) != h:
            raise ValueError('Reviewed source changed: ' + rel)
    sys.path.insert(0, str(repo / 'src'))
    from kaggriculture_research import environment
    if not Path(environment.__file__).resolve().is_relative_to(repo / 'src'):
        raise ValueError('Wrong project imports')
    if environment.engine_manifest()['files']['envs/kaggriculture/kaggriculture.py'] != ENGINE:
        raise ValueError('Engine hash changed')
    root = Path(restore['private_root']).resolve()
    if restore['episode_count'] != 7 or len(restore['downloaded_or_reused']) != 10:
        raise ValueError('Recovery scope differs')
    for obj in restore['downloaded_or_reused']:
        p = inside(root, obj['path'])
        if p.stat().st_size != obj['bytes'] or sha(p) != obj['sha256']:
            raise ValueError('Recovered object changed')
    for folder, names in [('kaggriculture_cash_realization', ('cash_features', 'callback')), ('kaggriculture_sale_timing', ('timing_features',))]:
        sys.path.insert(0, str(home / folder))
        for name in names:
            module = importlib.import_module(name)
            if Path(module.__file__).resolve() != (home / folder / (name + '.py')).resolve():
                raise ValueError('Wrong module: ' + name)
    fp = digest({'code': code_hash(BASE), 'protocol': sha(BASE / 'PROTOCOL.json'), 'engine': ENGINE, 'previous': sha(home / 'kaggriculture_maintenance_diagnosis/outputs/report.json'), 'commit': COMMIT, 'source_progress': sha(root / 'reports/staffing_progress.json')})
    write(OUT / 'preflight.json', {'status': 'PASSED', 'utc': utc(), 'fingerprint': fp, 'repo': str(repo), 'private_root': str(root), 'verified_objects': 10, 'source_commit': COMMIT, 'engine_sha256': ENGINE})
    log('PREFLIGHT_PASSED', verified_objects=10)
    return (root, environment, fp)

def source_jobs(root):
    progress = read(root / 'reports/staffing_progress.json')
    jobs = sorted((a for a in progress['artifact_manifest'] if a['arm'] == 'coordinated'), key=lambda a: (a['seed'], a['seat']))
    if [(a['seed'], a['seat']) for a in jobs] != [(1601, 0), (1601, 1), (1602, 0)]:
        raise ValueError('Wrong source groups')
    return (progress, jobs)

def load_source(root, progress, job):
    from kaggriculture_research.artifacts import load_checkpoint
    from kaggriculture_staffing.experiment import validate_episode
    path = inside(root, job['path'])
    key = {k: job[k] for k in KEYS}
    if sha(path) != job['sha256']:
        raise ValueError('Source hash differs')
    payload = load_checkpoint(path, {**progress['lineage'], **key})
    if payload is None:
        raise ValueError('Source lineage differs')
    validate_episode(payload, key)
    return (payload, key)

def samples():
    return sorted(set((479,528,695,696)) | set(range(480, 528)))

def save_csv(path, rows):
    import pandas as pd
    data = pd.DataFrame(rows).to_csv(index=False).encode()
    atomic(path, gzip.compress(data, mtime=0) if str(path).endswith('.gz') else data)

def test_stage():
    suite = unittest.defaultTestLoader.discover(str(BASE / 'tests'))
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    report = {'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped)}
    write(OUT / 'tests.json', report)
    if not result.wasSuccessful() or result.skipped:
        raise RuntimeError('Unit tests failed/skipped')
    return report

def common(fp):
    return {'utc': utc(), 'fingerprint': fp, 'code_sha256': code_hash(BASE), 'source_commit': COMMIT, 'engine_sha256': ENGINE, 'official_submission_score': None, 'official_metric_effect_measured': False, 'models_fit': 0, 'github_updated': False, 'cloud_resources_modified': False, 'feature_engineering_complete': False, 'validation_or_holdout_used': False}

def select_source(states):
    keys = sorted({(r['seed'], r['seat'], r['opponent'], r['arm']) for r in states if r['action_changed_in_window']})
    return dict(zip(KEYS, keys[0])) if keys else None

def screen(home):
    started = time.monotonic()
    tests = test_stage()
    root, environment, fp = preflight(home)
    game = environment.game
    from mechanics import validate
    from harvest_features import extract, FIELDS, SUMMARY_FIELDS, clock
    from harvest_policy import HarvestPolicy
    from harvest_experiment import measure, index_records
    mechanics = validate(game)
    write(OUT / 'mechanics.json', mechanics)
    log('MECHANICS_PASSED', sale_cases=mechanics['sale_cases'], demand_cases=mechanics['demand_cases'])
    progress, jobs = source_jobs(root)
    completed = []
    for job in jobs:
        key = {k: job[k] for k in KEYS}
        ident = digest(key)[:20]
        p = OUT / 'screen/checkpoints' / (ident + '.json.gz')
        cpf = digest({'run': fp, 'stage': 'screen', 'source': job['sha256']})
        cached = load_cache(p, cpf)
        if cached is None:
            payload, key = load_source(root, progress, job)
            indexed = index_records(payload)
            actor = HarvestPolicy(game, 'marginal')
            reference = HarvestPolicy(game, 'control')
            null = HarvestPolicy(game, 'null')
            states = []
            plants = []
            for step in samples():
                obs = deepcopy(indexed[step, key['seat']]['observation'])
                obs['step'] = clock(obs)
                for a in (actor, reference, null):
                    a.prime_recorded_clock(step - 1, key['seat'])
                before = digest(obs)
                rows, summary = extract(obs, game)
                actual, ms = measure(actor, obs, 'screen_candidate', emit)
                ref, rms = measure(reference, obs, 'screen_reference', emit)
                unchanged, nms = measure(null, obs, 'screen_null', emit)
                if unchanged != ref or ref != indexed[step, key['seat']]['action']:
                    raise ValueError('Null/reference/source action parity failed')
                in_window = step // 24 in (20, 21)
                if not in_window and actual != ref:
                    raise ValueError('Intervention outside window')
                if digest(obs) != before:
                    raise ValueError('Feature extraction mutated observation')
                changed = actual != ref
                states.append({**key, 'step': step, 'day': step // 24, 'hour': step % 24, 'candidate_callback_ms': ms, 'reference_callback_ms': rms, 'null_callback_ms': nms, 'action_changed_in_window': changed and in_window, 'farm_changed': (actual['farmer'], actual['hands']) != (ref['farmer'], ref['hands']), 'reference_action_parity': True, 'null_action_parity': True, 'candidate_action': json.dumps(actual,sort_keys=True), 'reference_action': json.dumps(ref,sort_keys=True), **summary})
                plants.extend(({**key, 'step': step, 'day': step // 24, 'hour': step % 24, **row} for row in rows))
            cached = {'key': key, 'states': states, 'plants': plants}
            save_cache(p, cpf, cached)
            log('SCREEN_EPISODE_SAVED', **key, states=len(states))
        else:
            log('SCREEN_EPISODE_REUSED', **key)
        completed.append(cached)
    states = [r for d in completed for r in d['states']]
    plants = [r for d in completed for r in d['plants']]
    if len(states) != 3 * len(samples()):
        raise ValueError('Incomplete screen')
    chosen = select_source(states)
    save_csv(OUT / 'screen/states.csv', states)
    save_csv(OUT / 'screen/task_features.csv.gz', plants)
    registry = []
    for field in FIELDS:
        values = [r[field] for r in plants]
        registry.append({'feature': field, 'distinct_values': len(set(values)), 'minimum': min(values, default=0), 'maximum': max(values, default=0), 'nonzero_fraction': sum((v != 0 for v in values)) / max(1, len(values)), 'status': 'activation_only_no_importance_claim'})
    save_csv(OUT / 'screen/feature_registry.csv', registry)
    report = {**common(fp), 'status': 'HARVEST_VALUE_SCREEN_COMPLETE', 'tests': tests, 'decision': 'ELIGIBLE_FOR_ONE_PAIRED_PILOT' if chosen else 'STOP_NO_ACTION_ACTIVATION', 'selected_key': chosen, 'observations': len(states), 'source_episodes': 3, 'independent_seed_blocks': 2, 'task_rows': len(plants), 'plant_descriptors': len(FIELDS), 'state_descriptors': len(SUMMARY_FIELDS), 'official_mechanics_fixtures': mechanics['sale_cases']+mechanics['demand_cases'], 'action_changes': sum((r['action_changed_in_window'] for r in states)), 'null_action_checks': len(states), 'source_action_checks': len(states), 'new_episode_transitions': 0, 'candidate_callback_max_ms': max((r['candidate_callback_ms'] for r in states)), 'elapsed_seconds': time.monotonic() - started, 'output_sha256': {n: sha(OUT / n) for n in ('mechanics.json', 'screen/states.csv', 'screen/task_features.csv.gz', 'screen/feature_registry.csv')}, 'limitations': ['Known development sources; turns and both seats are not independent samples.', 'Marginal liquidation assumes existing shed stock is sold first, no opponent trades, no travel or price forecast.', 'Live intervention only on zero-indexed days 20 and 21; other observations test unchanged behavior.', 'No official leaderboard score; inherited <=3-hands callback domain remains.']}
    write(OUT / 'screen/report.json', report)
    log(report['status'], decision=report['decision'], action_changes=report['action_changes'])

def verify_stage(stage):
    r = read(OUT / stage / 'report.json')
    s = read(OUT / stage / 'status.json')
    if s.get('status') != 'COMPLETED' or s.get('report_sha256') != sha(OUT / stage / 'report.json') or r['code_sha256'] != code_hash(BASE):
        raise ValueError('Stage report/code not verified')
    for rel, h in r.get('output_sha256', {}).items():
        if sha(inside(OUT, rel)) != h:
            raise ValueError('Stage output changed: ' + rel)
    return r

def pilot(home):
    started = time.monotonic()
    root, environment, fp = preflight(home)
    screen_report = verify_stage('screen')
    if screen_report['fingerprint'] != fp:
        raise ValueError('Screen lineage changed')
    if screen_report['selected_key'] is None:
        report = {**common(fp), 'status': 'HARVEST_VALUE_PILOT_COMPLETE', 'decision': 'STOP_NO_ACTION_ACTIVATION', 'completed_pairs': 0, 'prefix_replay_transitions': 0, 'suffix_transitions': 0, 'output_sha256': {}, 'elapsed_seconds': time.monotonic() - started}
        write(OUT / 'pilot/report.json', report)
        log(report['status'], decision=report['decision'])
        return
    from harvest_experiment import rollout, paired, decision
    import pandas as pd
    progress, jobs = source_jobs(root)
    job = next((j for j in jobs if {k: j[k] for k in KEYS} == screen_report['selected_key']))
    payload, key = load_source(root, progress, job)
    prior = pd.read_csv(home / 'kaggriculture_sale_timing/outputs/final_comparisons.csv').to_dict('records')
    expected = next((r for r in prior if all((r[k] == key[k] for k in KEYS))))
    branches = []
    new_prefix = new_suffix = 0
    for mode in ('control', 'marginal'):
        ident = digest(key)[:20]
        p = OUT / 'pilot/checkpoints' / f'{ident}-{mode}.json.gz'
        cpf = digest({'run': fp, 'stage': 'pilot', 'source': job['sha256'], 'mode': mode})
        branch = load_cache(p, cpf)
        if branch is None:
            branch = rollout(payload, key, mode, environment.game, environment.make_environment, expected, emit, log)
            save_cache(p, cpf, branch)
            new_prefix += branch['prefix_replay_transitions']
            new_suffix += branch['suffix_transitions']
            log('BRANCH_CHECKPOINT_SAVED', mode=mode, **key)
        else:
            log('BRANCH_REUSED', mode=mode, **key)
        branches.append(branch)
    row = paired(*branches)
    save_csv(OUT / 'pilot/paired_results.csv', [row])
    save_csv(OUT / 'pilot/trajectories.csv', [{**b['key'], **r} for b in branches for r in b['trace']])
    report = {**common(fp), 'status': 'HARVEST_VALUE_PILOT_COMPLETE', 'decision': decision(row), 'completed_pairs': 1, 'paired_results': [row], 'new_prefix_replay_transitions': new_prefix, 'new_suffix_transitions': new_suffix, 'represented_prefix_transitions': 960, 'represented_suffix_transitions': 478, 'full_seasons_recomputed_from_policy': 0, 'official_replay_prefix_branches': 2, 'null_action_checks': sum((b['null_action_checks'] for b in branches)), 'candidate_callback_max_ms': max((r['candidate_callback_ms'] for b in branches for r in b['trace'])), 'elapsed_seconds': time.monotonic() - started, 'output_sha256': {n: sha(OUT / n) for n in ('pilot/paired_results.csv', 'pilot/trajectories.csv')}, 'limitations': ['One action-activated development source; not independent validation.', 'We replay a recorded prefix in the real seeded evaluator, then recompute both policies to the endpoint.', 'Only two HARVEST priority-value terms differ in days 20-21; all other policy formulas stay fixed. Downstream purchases, sales and crop states may change.', 'Market rule unchanged, not necessarily market quantities; state-mediated changes are intended.', 'Family not ready for promotion on one positive pair; distinct opponents and new groups remain necessary.', 'AWS bills continue until the application is stopped; local stage timeout does not stop AWS.']}
    write(OUT / 'pilot/report.json', report)
    log(report['status'], decision=report['decision'], coins_delta=row['coins_delta'])

def supervise(stage, home):
    path = OUT / stage / 'status.json'
    if path.exists():
        status = read(path)
        if status.get('status') == 'COMPLETED':
            r = verify_stage(stage)
            _,_,current_fp=preflight(home)
            if current_fp!=r['fingerprint']: raise ValueError('Completed stage lineage changed')
            log('VERIFIED_STAGE_REUSED', name=stage, decision=r['decision'])
            return
        raise RuntimeError('Prior stage failed/active/interrupted. Bundle diagnostics; no unchanged retry.')
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('x') as f:
            json.dump({'status': 'RUNNING', 'utc': utc()}, f)
    except FileExistsError:
        raise RuntimeError('Another launch created the stage lock')
    child = None
    try:
        child = subprocess.Popen([sys.executable, str(BASE / 'run_harvest.py'), '_' + stage, '--home', str(home)], start_new_session=True)
        tick = time.monotonic()
        beat = tick
        while child.poll() is None:
            now = time.monotonic()
            if now - tick > CAPS[stage]:
                raise TimeoutError(str(CAPS[stage]) + ' second stage cap reached')
            if now - beat >= 10:
                log('HEARTBEAT', name=stage, elapsed_seconds=round(now - tick, 1))
                beat = now
            time.sleep(0.2)
        if child.returncode:
            raise RuntimeError('Stage failed; bundle diagnostics instead of retrying')
        write(path, {'status': 'COMPLETED', 'utc': utc(), 'report_sha256': sha(OUT / stage / 'report.json')})
    except BaseException:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        write(path, {'status': 'FAILED', 'utc': utc()})
        raise

def bundle():
    paths = [p for p in OUT.rglob('*') if p.is_file() and (not p.is_symlink()) and (p.suffix in ('.json', '.jsonl', '.csv', '.gz', '.html', '.txt'))]
    paths += [BASE / n for n in ('14_harvest_value_feature_ablation.ipynb', 'PROTOCOL.json', 'FEATURE_RESEARCH.md', 'LOCAL_VALIDATION.json', 'reference/input_review.json')]
    paths = [p for p in paths if p.exists()]
    if any((p.stat().st_size > 50000000 for p in paths)) or sum((p.stat().st_size for p in paths)) > 150000000:
        raise ValueError('Unexpectedly large output')
    manifest = {'utc': utc(), 'files': {str(p.relative_to(BASE)): sha(p) for p in paths}}
    dest = BASE / 'kaggriculture_harvest_value_results.zip'
    fd, temp = tempfile.mkstemp(prefix='.bundle-', dir=BASE)
    os.close(fd)
    try:
        with zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED) as z:
            for p in paths:
                z.write(p, str(p.relative_to(BASE)))
            z.writestr('BUNDLE_MANIFEST.json', json.dumps(manifest, indent=2))
        os.replace(temp, dest)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    print('RESULTS_BUNDLE:', dest, flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['screen', 'pilot', '_screen', '_pilot', 'tests', 'bundle'])
    parser.add_argument('--home', type=Path, default=Path.home())
    args = parser.parse_args()
    try:
        if args.command == 'bundle':
            bundle()
        elif args.command == 'tests':
            test_stage()
        elif args.command.startswith('_'):
            {'_screen': screen, '_pilot': pilot}[args.command](args.home)
        else:
            supervise(args.command, args.home)
    except BaseException as e:
        write(OUT / ('failure_' + args.command + '.json'), {'utc': utc(), 'command': args.command, 'error': str(e), 'traceback': traceback.format_exc()})
        raise
if __name__ == '__main__':

    def stop(sig, frame):
        raise KeyboardInterrupt('Stop requested; completed checkpoints preserved')
    signal.signal(signal.SIGTERM, stop)
    main()
