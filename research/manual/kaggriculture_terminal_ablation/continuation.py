"""Paired, reactive day-29 continuation. Policies never receive evaluator records.

The unchanged notebook-08 CashPolicy differs only in the input used to construct
SELL quantities. A same-state shadow callback proves action-level attribution.
Separate control/aligned trajectories may subsequently choose different farm
commands because their states differ. That is a downstream effect, not a new rule.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import math
import time

LEGAL = ('player','step','day','hour','farms','private','market','town')
START, END, LIMIT_MS = 696, 718, 500.0


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def legal_observation(value):
    obs = {k: deepcopy(value[k]) for k in LEGAL if k != 'step'}
    step = obs['day']*24 + obs['hour']
    if value.get('step') is not None and value['step'] != step:
        raise ValueError('Conflicting source callback clock')
    if not START <= step <= END or obs['player'] not in (0,1):
        raise ValueError('Outside registered terminal callback')
    obs['step'] = step
    return obs


def index_episode(payload):
    indexed = {}
    for row in payload['records']:
        obs = row['observation']; step = obs['day']*24+obs['hour']
        if START <= step <= END:
            key = (step,row['player'])
            if key in indexed or obs['player'] != row['player']:
                raise ValueError('Duplicate/misaligned recorded callback')
            indexed[key] = row
    if set(indexed) != {(s,p) for s in range(START,END+1) for p in (0,1)}:
        raise ValueError('Incomplete terminal suffix')
    return indexed


def make_actors(source_arm, variant, seat):
    from callback import CashPolicy
    from kaggriculture_livestock.policy import LivestockPolicy
    candidate = CashPolicy(source_arm, variant)
    candidate.prime_recorded_clock(START-1,seat)
    rival = LivestockPolicy.from_state_dict({'arm':'fertilizer','last_step':START-1,'player':1-seat})
    if rival.state_dict() != {'arm':'fertilizer','last_step':START-1,'player':1-seat}:
        raise ValueError('Unexpected rival memory restoration')
    shadow = CashPolicy(source_arm,'control')
    shadow.prime_recorded_clock(START-1,seat)
    return candidate,rival,shadow


def project_next(result):
    # Outcomes and status remain evaluator-only. Actors receive precisely LEGAL.
    return [legal_observation(r) for r in result]


def local_match(margin):
    if not math.isfinite(margin):
        raise ValueError('Invalid coin margin')
    return float(margin > 0) + .5*float(margin == 0)


def terminal_metrics(result, seat, products):
    if any(r['status'] != 'DONE' or r['day']*24+r['hour'] != END+1 for r in result):
        raise ValueError('Continuation did not end at state 719')
    for p in (0,1):
        if result[p]['reward'] != result[p]['farms'][p]['money']:
            raise ValueError('Terminal reward differs from banked cash')
    ours = float(result[seat]['reward']); theirs = float(result[1-seat]['reward'])
    if not all(math.isfinite(x) for x in (ours,theirs)):
        raise ValueError('Invalid terminal reward')
    private = result[seat]['private']
    shed = sum(n for item,n in private['shed'].items() if item in products)
    carried = sum(n for inv in private['inventories'] for item,n in inv.items() if item in products)
    return {'coins':ours,'opponent_coins':theirs,'coin_margin':ours-theirs,
            'local_match_score':local_match(ours-theirs),
            'residual_shed_product_units':shed,'residual_carried_product_units':carried,
            'residual_product_units':shed+carried}


def rollout(payload, key, variant, game, transition, assert_source, emit,
            actor_factory=make_actors, context_extractor=None):
    """Evaluate exactly 23 successive decisions, never reset after a cash effect."""
    if variant not in ('control','aligned') or key['arm'] not in ('coordinated','sequential'):
        raise ValueError('Unknown source or treatment arm')
    if key['opponent'] != 'livestock_fertilizer' or key['seat'] not in (0,1):
        raise ValueError('Unregistered opponent/seat')
    records = index_episode(payload); seat = key['seat']
    current = [legal_observation(records[(START,p)]['observation']) for p in (0,1)]
    initial = digest(current)
    candidate,rival,shadow = actor_factory(key['arm'],variant,seat)
    trace=[]; feature_rows=[]; candidate_actions=[]; rival_actions=[]
    parity_checks=0
    for step in range(START,END+1):
        own,riv = current[seat],current[1-seat]
        before = digest(current)
        actions={};elapsed={};diagnostics={}
        # Every actor sees only its own legal view; never the other's private data.
        for name,actor,obs in (('candidate',candidate,own),('opponent',rival,riv)):
            arg=deepcopy(obs); old=digest(arg)
            tick=time.perf_counter(); actions[name]=actor(arg)
            elapsed[name]=(time.perf_counter()-tick)*1000
            if digest(arg)!=old:
                raise ValueError(name+' mutated its legal observation')
        diagnostics=deepcopy(candidate.last_diagnostics)
        if not diagnostics.get('active') or not diagnostics.get('base_rule_parity'):
            raise ValueError('Missing terminal attribution diagnostics')
        if variant=='aligned':
            arg=deepcopy(own); old=digest(arg)
            tick=time.perf_counter(); shadow_action=shadow(arg)
            elapsed['same_state_control']=(time.perf_counter()-tick)*1000
            if digest(arg)!=old:
                raise ValueError('Same-state control mutated input')
        else:
            shadow_action=actions['candidate']
        from cash_features import non_sell_orders
        invariant = all(actions['candidate'][k]==shadow_action[k] for k in ('farmer','hands'))
        invariant &= non_sell_orders(actions['candidate']) == non_sell_orders(shadow_action)
        invariant &= shadow_action == diagnostics['control_action']
        row={'step':step,'variant':variant,'same_state_attribution_passed':bool(invariant),
             'market_changed_on_same_state':actions['candidate']['market']!=shadow_action['market'],
             'candidate_callback_ms':elapsed['candidate'],'opponent_callback_ms':elapsed['opponent'],
             'same_state_control_callback_ms':elapsed.get('same_state_control',0.0),
             'own_observation_sha256':digest(own),'opponent_observation_sha256':digest(riv),
             'own_cash_before':own['farms'][seat]['money'],
             'opponent_cash_before':own['farms'][1-seat]['money']}
        sample={'sample':row,'candidate_action':actions['candidate'],'opponent_action':actions['opponent'],
                'same_state_control_action':shadow_action}
        emit('CALLBACK_MEASURED',sample)
        if not invariant or digest(current)!=before:
            raise ValueError('Same-state attribution/input-isolation failed')
        if any(not math.isfinite(v) or v<0 or v>LIMIT_MS for v in elapsed.values()):
            raise RuntimeError('500 ms callback gate breached; sample saved before gate')
        if variant=='control':
            if actions['candidate']!=records[(step,seat)]['action']:
                raise ValueError('Live control action differs from recorded action')
            if actions['opponent']!=records[(step,1-seat)]['action']:
                raise ValueError('Live opponent action differs from recorded action')
        extra = context_extractor(own,game.PRODUCTS,game.market_price) if context_extractor else {}
        feature_rows.append({'step':step,'variant':variant,**diagnostics['features'],**extra})
        result=transition(own,riv,actions['candidate'],actions['opponent'],game)
        if variant=='control':
            nxt={p:records[(step+1,p)] for p in (0,1)} if step<END else None
            assert_source(result,nxt,payload['rewards'],step)
            parity_checks+=1
        row.update(own_cash_after=result[seat]['farms'][seat]['money'],
                   opponent_cash_after=result[1-seat]['farms'][1-seat]['money'],
                   next_public_state_sha256=digest({k:result[seat][k] for k in ('day','hour','farms','market','town')}))
        trace.append(row)
        candidate_actions.append(deepcopy(actions['candidate']));rival_actions.append(deepcopy(actions['opponent']))
        emit('TRANSITION_COMPLETED',{'step':step,'variant':variant,
              'own_cash_after':row['own_cash_after'],'opponent_cash_after':row['opponent_cash_after']})
        if step<END:
            current=project_next(result)
    return {'key':key,'variant':variant,'initial_state_sha256':initial,
            'metrics':terminal_metrics(result,seat,game.PRODUCTS),'trace':trace,'features':feature_rows,
            'candidate_actions':candidate_actions,'opponent_actions':rival_actions,
            'control_recorded_transition_parity_checks':parity_checks,
            'transitions':len(trace),'final_state_sha256':digest(result)}


def pair_results(control, aligned):
    if control['key'] != aligned['key'] or control['initial_state_sha256'] != aligned['initial_state_sha256']:
        raise ValueError('Paired branches do not share key and initial state')
    if control['variant'] != 'control' or aligned['variant'] != 'aligned':
        raise ValueError('Invalid paired arm identity')
    for b in (control,aligned):
        if b['transitions']!=23 or len(b['trace'])!=23:
            raise ValueError('Cannot score partial suffix')
    if control['control_recorded_transition_parity_checks']!=23:
        raise ValueError('Control suffix not reproduced')
    fields = ('coins','opponent_coins','coin_margin','local_match_score','residual_product_units',
              'residual_shed_product_units','residual_carried_product_units')
    row={**control['key'],'initial_state_sha256':control['initial_state_sha256']}
    for f in fields:
        row[f+'_control']=control['metrics'][f];row[f+'_aligned']=aligned['metrics'][f]
        row[f+'_delta']=aligned['metrics'][f]-control['metrics'][f]
    row['own_action_changes_across_trajectories']=sum(a!=b for a,b in zip(control['candidate_actions'],aligned['candidate_actions'],strict=True))
    row['opponent_action_changes_across_trajectories']=sum(a!=b for a,b in zip(control['opponent_actions'],aligned['opponent_actions'],strict=True))
    row['same_state_market_changes']=sum(r['market_changed_on_same_state'] for r in aligned['trace'])
    row['role']='primary_intervention' if row['arm']=='coordinated' else 'negative_control'
    if row['role']=='negative_control':
        if control['final_state_sha256'] != aligned['final_state_sha256'] or any(row[f+'_delta']!=0 for f in fields) or row['own_action_changes_across_trajectories'] or row['opponent_action_changes_across_trajectories']:
            raise ValueError('Sequential negative control diverged; implementation must be reviewed')
    return row


def decision(rows, all_pairs_completed):
    primary=[r for r in rows if r['role']=='primary_intervention']
    if any(r['coins_delta']<0 or r['coin_margin_delta']<0 or r['local_match_score_delta']<0 for r in primary):
        return 'STOP_NEGATIVE_TERMINAL_EFFECT'
    if not all_pairs_completed:
        return 'INCOMPLETE_NO_PERFORMANCE_CONCLUSION'
    if not any(r['same_state_market_changes'] for r in primary):
        return 'STOP_NO_ACTIVATION'
    if not any(r['coins_delta']>0 or r['coin_margin_delta']>0 or r['local_match_score_delta']>0 for r in primary):
        return 'STOP_NO_TERMINAL_BENEFIT'
    return 'PROMISING_REQUIRES_FRESH_GROUPS_AND_DISTINCT_OPPONENTS'
