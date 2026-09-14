"""Evaluator only. Replay an official prefix; then advance a reactive suffix.

Seeds and both private views exist here for evaluation, NEVER as feature inputs.
Actual make_environment preserves the official weed/shop randomness. No invented
randomness, manual time advancement, or injection of future recorded shops.
"""
from __future__ import annotations
from copy import deepcopy
import math, time
from research_io import digest
from lifecycle_features import clock
START, END = (192, 718)
FIELDS = ('player', 'step', 'day', 'hour', 'farms', 'market', 'town', 'private')

def index_records(payload):
    out = {}
    for r in payload['records']:
        key = (clock(r['observation']), r['player'])
        if key in out:
            raise ValueError('Duplicate source observation')
        out[key] = r
    if set(out) != {(s, p) for s in range(719) for p in (0, 1)}:
        raise ValueError('Incomplete full source records')
    return out

def legal_env_observations(env):
    root = env.state[0].observation
    observations = []
    for player in (0, 1):
        private = env.state[player].observation.private
        observations.append({'player': player, 'day': int(root.day), 'hour': int(root.hour), 'step': int(root.day) * 24 + int(root.hour), 'farms': deepcopy(root.farms), 'market': deepcopy(root.market), 'town': deepcopy(root.town), 'private': deepcopy(private)})
    return observations

def compare_recorded(current, records, step):
    for player in (0, 1):
        r = records[step, player]['observation']
        for field in ('player', 'day', 'hour', 'farms', 'market', 'town', 'private'):
            if current[player][field] != r[field]:
                raise ValueError(f'Source replay mismatch at {step}, seat {player}, field {field}')

def measure(actor, obs, role, emit):
    arg = deepcopy(obs)
    before = digest(arg)
    tick = time.perf_counter()
    action = actor(arg)
    elapsed = (time.perf_counter() - tick) * 1000
    emit('CALLBACK', {'step': obs['step'], 'role': role, 'milliseconds': elapsed, 'action': action})
    if digest(arg) != before:
        raise ValueError('Actor mutated its legal observation')
    if not math.isfinite(elapsed) or not 0 <= elapsed <= 500:
        raise RuntimeError('500 ms callback gate exceeded; sample saved')
    return (action, elapsed)

def actors(game, mode, seat, arm):
    from lifecycle_policy import LifecyclePolicy
    from kaggriculture_livestock.policy import LivestockPolicy
    candidate = LifecyclePolicy(game, mode, arm)
    reference = LifecyclePolicy(game, 'control', arm)
    null = LifecyclePolicy(game, 'null', arm)
    for actor in (candidate, reference, null):
        actor.prime_recorded_clock(START - 1, seat)
    rival = LivestockPolicy.from_state_dict({'arm': 'fertilizer', 'last_step': START - 1, 'player': 1 - seat})
    return (candidate, reference, null, rival)

def rollout(payload, key, mode, game, make_environment, expected, emit, progress, actor_factory=actors):
    if key['arm'] != 'coordinated' or mode not in ('control', 'retire', 'renew'):
        raise ValueError('Unregistered branch')
    records = index_records(payload)
    seat = key['seat']
    env = make_environment(key['seed'])
    if env.configuration.get('seed') is not None:
        raise ValueError('Seed exposed in actor configuration')
    for step in range(START):
        current = legal_env_observations(env)
        compare_recorded(current, records, step)
        env.step([deepcopy(records[step, p]['action']) for p in (0, 1)])
        if (step + 1) % 120 == 0:
            progress('PREFIX_REPLAY', mode=mode, completed=step + 1, total=START)
    current = legal_env_observations(env)
    compare_recorded(current, records, START)
    initial = digest(current)
    candidate, reference, null, rival = actor_factory(game, mode, seat, key['arm'])
    traces = []
    null_checks = 0
    source_checks = 0
    for step in range(START, END + 1):
        current = legal_env_observations(env)
        if clock(current[seat]) != step:
            raise ValueError('Live clock differs')
        action, ms = measure(candidate, current[seat], 'candidate', emit)
        ref, rms = measure(reference, current[seat], 'same_state_control', emit)
        unchanged, nms = measure(null, current[seat], 'same_state_null_fork', emit)
        enemy, ems = measure(rival, current[1 - seat], 'opponent', emit)
        if unchanged != ref:
            raise ValueError('Null fork changed decisions')
        null_checks += 1
        active = 8 <= step // 24 <= 27
        if (mode == 'control' or not active) and action != ref:
            raise ValueError('Action intervention escaped its window')
        if mode == 'control' and step < END:
            if action != records[step, seat]['action'] or enemy != records[step, 1 - seat]['action']:
                raise ValueError('Control action does not reproduce source')
        commands = [action['farmer'], *action['hands']]
        refs = [ref['farmer'], *ref['hands']]
        r = {'step': step, 'day': step // 24, 'mode': mode, 'candidate_callback_ms': ms, 'reference_callback_ms': rms, 'null_callback_ms': nms, 'opponent_callback_ms': ems, 'same_state_action_changed': action != ref, 'same_state_farm_changed': commands != refs, 'water_commands': sum((a[0] == 'WATER' for a in commands)), 'reference_water_commands': sum((a[0] == 'WATER' for a in refs)), 'harvest_commands': sum((a[0] == 'HARVEST' for a in commands)), 'plant_commands': sum((a[0] == 'PLANT' for a in commands)), 'own_cash_before': current[seat]['farms'][seat]['money']}
        r['market_prices'] = deepcopy(current[seat]['market']['prices'])
        r['market_inventory'] = deepcopy(current[seat]['market']['inventory'])
        r['public_shops'] = list(current[seat]['town']['unlocked_shops'])
        r['own_plants_before'] = [{'x':x,'y':y,**deepcopy(t)} for y,row in enumerate(current[seat]['farms'][seat]['tiles']) for x,t in enumerate(row) if isinstance(t,dict) and t.get('kind')=='PLANT']
        r['own_shed_before'] = deepcopy(current[seat]['private']['shed'])
        r['dig_commands'] = sum(a[0]=='DIG' for a in commands)
        r['action'] = deepcopy(action)
        r['opponent_action'] = deepcopy(enemy)
        r['same_state_reference_action'] = deepcopy(ref)
        actions = [None, None]
        actions[seat] = action
        actions[1 - seat] = enemy
        env.step(actions)
        nxt = legal_env_observations(env)
        if mode == 'control' and step < END:
            compare_recorded(nxt, records, step + 1)
            source_checks += 1
        r.update(own_cash=nxt[seat]['farms'][seat]['money'], opponent_cash=nxt[seat]['farms'][1 - seat]['money'])
        traces.append(r)
        if (step - START + 1) % 48 == 0:
            progress('SUFFIX_PROGRESS', mode=mode, completed=step - START + 1, total=END - START + 1)
    if any((s.status != 'DONE' for s in env.state)) or len(env.steps) != 720:
        raise ValueError('Incomplete official horizon')
    rewards = [float(s.reward) for s in env.state]
    if any((rewards[p] != nxt[p]['farms'][p]['money'] for p in (0, 1))):
        raise ValueError('Reward/cash mismatch')
    if mode == 'control' and (rewards[seat] != expected['coins_guarded'] or rewards[1 - seat] != expected['opponent_coins_guarded']):
        raise ValueError('Control endpoint differs from notebook10')
    margin = rewards[seat] - rewards[1 - seat]
    private = nxt[seat]['private']
    residual = sum((n for inv in [private['shed'], *private['inventories']] for item, n in inv.items() if item in game.PRODUCTS))
    return {'key': key, 'mode': mode, 'initial_sha256': initial, 'prefix_replay_transitions': START, 'suffix_transitions': END - START + 1, 'null_action_checks': null_checks, 'control_source_transition_checks': source_checks, 'trace': traces, 'metrics': {'coins': rewards[seat], 'opponent_coins': rewards[1 - seat], 'coin_margin': margin, 'local_match_score': float(margin > 0) + 0.5 * float(margin == 0), 'residual_product_units': residual}, 'final_state_sha256': digest(nxt)}

def paired(control, candidate):
    if control['key'] != candidate['key'] or control['initial_sha256'] != candidate['initial_sha256']:
        raise ValueError('Branches do not share initial conditions')
    if control['mode'] != 'control' or candidate['mode'] not in ('retire','renew'):
        raise ValueError('Wrong paired modes')
    for branch in (control, candidate):
        if branch['suffix_transitions'] != 527 or branch['null_action_checks'] != 527:
            raise ValueError('Incomplete branch; no endpoint score')
    if control['control_source_transition_checks'] != 526:
        raise ValueError('Control source not reproduced')
    out = {**control['key'], 'contrast':candidate['mode']+'-control'}
    for metric in control['metrics']:
        out[metric + '_control'] = control['metrics'][metric]
        out[metric + '_candidate'] = candidate['metrics'][metric]
        out[metric + '_delta'] = candidate['metrics'][metric] - control['metrics'][metric]
    out['same_state_action_changes'] = sum((t['same_state_action_changed'] for t in candidate['trace']))
    out['water_commands_control'] = sum((t['water_commands'] for t in control['trace']))
    out['water_commands_candidate'] = sum((t['water_commands'] for t in candidate['trace']))
    return out

def decision(row):
    if any((row[k + '_delta'] < 0 for k in ('coins', 'coin_margin', 'local_match_score'))):
        return 'STOP_NEGATIVE_ENDPOINT'
    if not row['same_state_action_changes']:
        return 'STOP_NO_TRAJECTORY_ACTIVATION'
    if not any((row[k + '_delta'] > 0 for k in ('coins', 'coin_margin', 'local_match_score'))):
        return 'STOP_NO_ENDPOINT_BENEFIT'
    return 'PROMISING_SINGLE_DEVELOPMENT_PAIR_REQUIRES_VALIDATION'
