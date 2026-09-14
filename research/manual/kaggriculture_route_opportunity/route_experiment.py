"""EVALUATOR ONLY: short reactive trajectories, separate from causal features."""
from copy import deepcopy
import math,time
from route_io import digest

START,END=696,718
METRICS=('coins','opponent_coins','coin_margin','local_match_score','residual_product_units')


def measure(actor,obs,role,emit):
    arg=deepcopy(obs);before=digest(arg)
    t=time.perf_counter();action=actor(arg);elapsed=(time.perf_counter()-t)*1000
    emit('CALLBACK',{'step':obs['step'],'role':role,'callback_ms':elapsed,'action':action})
    if digest(arg)!=before:raise ValueError('Actor mutated legal observation')
    if not math.isfinite(elapsed) or not 0<=elapsed<=500:
        raise RuntimeError('500 ms callback gate breached; offending sample preserved')
    return action,elapsed


def make_actors(source_arm,mode,seat):
    from route_policy import RouteOpportunityPolicy
    from timing_features import FinalSalePolicy
    from kaggriculture_livestock.policy import LivestockPolicy
    candidate=RouteOpportunityPolicy(source_arm,mode)
    candidate.prime_recorded_clock(START-1,seat)
    reference=FinalSalePolicy(source_arm);reference.prime_recorded_clock(START-1,seat)
    opponent=LivestockPolicy.from_state_dict({'arm':'fertilizer','last_step':START-1,'player':1-seat})
    return candidate,opponent,reference


def rollout(payload,key,mode,game,mods,emit,expected,actor_factory=make_actors):
    """Exactly 23 linked decisions. No original-state reset after treatment."""
    if mode not in ('control','opportunity') or key['opponent']!='livestock_fertilizer':
        raise ValueError('Unknown branch/opponent')
    cont=mods['continuation'];records=cont.index_episode(payload);seat=key['seat']
    current=[cont.legal_observation(records[(START,p)]['observation']) for p in (0,1)]
    initial=digest(current)
    candidate,rival,reference=actor_factory(key['arm'],mode,seat)
    traces=[];commands=[];rival_commands=[];source_checks=0
    for step in range(START,END+1):
        obs,other=current[seat],current[1-seat]
        action,ms=measure(candidate,obs,'candidate',emit)
        rival_action,rms=measure(rival,other,'opponent',emit)
        ref,rfs=measure(reference,obs,'same_state_reference',emit)
        d=deepcopy(candidate.last_diagnostics)
        if not d.get('active') or d['same_state_control_action']!=ref:
            raise ValueError('Reference rule/clock parity failed on current state')
        if mode=='control' and action!=ref:raise ValueError('Disabled-family callback changed actions')
        if key['arm']=='sequential' and action!=ref:raise ValueError('Negative control changed actions')
        ns=lambda a:[o for o in a['market'] if not o or o[0]!='SELL']
        if ns(action)!=ns(ref) or (step<END and action['market']!=ref['market']):
            raise ValueError('Same-state market/hiring rule changed')
        result=mods['run_cash'].isolated_transition(obs,other,action,rival_action,game)
        if mode=='control':
            if rival_action!=records[(step,1-seat)]['action']:raise ValueError('Control opponent differs from source')
            if step<END:
                if action!=records[(step,seat)]['action']:raise ValueError('Control prefix differs from recorded source')
                nxt={p:records[(step+1,p)] for p in (0,1)}
                mods['run_cash'].assert_source_transition(result,nxt,payload['rewards'],step)
            source_checks+=1
        routing=d['routing']
        trace={'step':step,'mode':mode,'candidate_callback_ms':ms,'opponent_callback_ms':rms,
               'reference_callback_ms':rfs,'own_cash':result[seat]['farms'][seat]['money'],
               'opponent_cash':result[1-seat]['farms'][1-seat]['money'],
               'same_state_farm_changed':any(action[k]!=ref[k] for k in ('farmer','hands')),
               'same_state_market_changed':action['market']!=ref['market'],
               'static_utility_delta':routing['static_utility_delta'],
               'static_key_improved':routing['static_key_improved'],
               'prior_state_sha256':digest(current),'next_state_sha256':digest(result)}
        emit('TRANSITION',trace);traces.append(trace)
        commands.append(deepcopy(action));rival_commands.append(deepcopy(rival_action))
        if step<END:current=cont.project_next(result)
    metrics=cont.terminal_metrics(result,seat,game.PRODUCTS)
    if mode=='control':
        for k in METRICS:
            if metrics[k]!=expected[k+'_guarded']:
                raise ValueError('Control terminal endpoint differs from notebook10: '+k)
    return {'key':key,'mode':mode,'initial_state_sha256':initial,'final_state_sha256':digest(result),
            'metrics':{k:metrics[k] for k in METRICS},'trace':traces,'candidate_actions':commands,
            'opponent_actions':rival_commands,'transitions':len(traces),
            'reference_checks':len(traces),'source_checks':source_checks}


def paired(control,treatment):
    if control['key']!=treatment['key'] or control['initial_state_sha256']!=treatment['initial_state_sha256']:
        raise ValueError('Not a matched pair')
    if control['mode']!='control' or treatment['mode']!='opportunity':raise ValueError('Wrong arm labels')
    if any(x['transitions']!=23 or len(x['trace'])!=23 for x in (control,treatment)):
        raise ValueError('Partial branches cannot be scored')
    if control['source_checks']!=23:raise ValueError('Unverified control reproduction')
    row={**control['key'],'role':'primary' if control['key']['arm']=='coordinated' else 'negative_control'}
    for k in METRICS:
        row[k+'_control']=control['metrics'][k];row[k+'_candidate']=treatment['metrics'][k]
        row[k+'_delta']=treatment['metrics'][k]-control['metrics'][k]
    row['same_state_farm_changes']=sum(t['same_state_farm_changed'] for t in treatment['trace'])
    row['opponent_action_changes']=sum(a!=b for a,b in zip(control['opponent_actions'],treatment['opponent_actions'],strict=True))
    if row['role']=='negative_control' and (control['final_state_sha256']!=treatment['final_state_sha256'] or
            any(row[k+'_delta']!=0 for k in METRICS) or control['candidate_actions']!=treatment['candidate_actions']):
        raise ValueError('Negative control diverged')
    return row


def decision(rows):
    primary=[r for r in rows if r['role']=='primary']
    if not primary:return 'INCOMPLETE_NO_PRIMARY_RESULT'
    if any(r['coins_delta']<0 or r['coin_margin_delta']<0 or r['local_match_score_delta']<0 for r in primary):
        return 'STOP_NEGATIVE_ENDPOINT'
    if not any(r['same_state_farm_changes'] for r in primary):return 'STOP_NO_TRAJECTORY_ACTIVATION'
    if not any(r['coins_delta']>0 or r['coin_margin_delta']>0 or r['local_match_score_delta']>0 for r in primary):
        return 'STOP_NO_ENDPOINT_BENEFIT'
    return 'PROMISING_SINGLE_DEVELOPMENT_PAIR_NOT_VALIDATED'
