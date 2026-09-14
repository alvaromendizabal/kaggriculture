"""One new clear-only continuation. Evaluator metadata never enters features."""
from __future__ import annotations
from copy import deepcopy
import math
import time
from factorial_io import digest
from lifecycle_features import clock
from joint_features import extract
START,END=192,718


def observations(env):
    root=env.state[0].observation
    return [dict(player=p,day=int(root.day),hour=int(root.hour),step=int(root.day)*24+int(root.hour),
      farms=deepcopy(root.farms),market=deepcopy(root.market),town=deepcopy(root.town),private=deepcopy(env.state[p].observation.private)) for p in (0,1)]


def indexed_source(payload):
    result={}
    for r in payload['records']:
        k=(clock(r['observation']),r['player'])
        if k in result: raise ValueError('Duplicate raw source record')
        result[k]=r
    if set(result)!={(s,p) for s in range(719) for p in (0,1)}: raise ValueError('Incomplete source')
    return result


def compare_source(obs,source,step):
    for p in (0,1):
        for f in ('player','day','hour','farms','market','town','private'):
            if obs[p][f]!=source[step,p]['observation'][f]: raise ValueError(f'Source mismatch step={step} seat={p} field={f}')


def measure(actor,obs,role,emit):
    arg=deepcopy(obs);before=digest(arg);tick=time.perf_counter()
    a=actor(arg);ms=(time.perf_counter()-tick)*1000
    emit('CALLBACK',{'step':obs['step'],'role':role,'milliseconds':ms,'action':a})
    if digest(arg)!=before: raise ValueError('Actor mutated observation')
    if not math.isfinite(ms) or not 0<=ms<=500: raise RuntimeError('500 ms callback gate exceeded; measurement saved')
    return a,ms


def make_actors(game,key,start):
    from factorial_policy import FactorialPolicy
    from kaggriculture_livestock.policy import LivestockPolicy
    c=FactorialPolicy(game,'clear_only');r=FactorialPolicy(game,'control');n=FactorialPolicy(game,'null')
    for a in (c,r,n): a.prime_recorded_clock(start-1,key['seat'])
    rival=LivestockPolicy.from_state_dict({'arm':'fertilizer','last_step':start-1,'player':1-key['seat']})
    return c,r,n,rival


def screen_block(payload,key,old_control,game,layout,start,end,emit,actor_factory=make_actors):
    raw=indexed_source(payload);seat=key['seat'];old={r['step']:r for r in old_control['trace']}
    c,r,n,_=actor_factory(game,key,start)
    records=[]
    for step in range(start,end+1):
        obs=deepcopy(raw[step,seat]['observation']);obs['step']=clock(obs)
        before=digest(obs);features=extract(obs,game,layout)
        ca,cm=measure(c,obs,'clear_only_screen',emit);ra,rm=measure(r,obs,'control_screen',emit);na,nm=measure(n,obs,'null_screen',emit)
        if ra!=na or ra!=old[step]['action']: raise ValueError('Original/null/archived control parity failed')
        if obs['farms'][seat]['money']!=old[step]['own_cash_before']: raise ValueError('Control input cash differs')
        if obs['private']['shed']!=old[step]['own_shed_before']: raise ValueError('Control shed differs')
        if not 8<=step//24<=27 and ca!=ra: raise ValueError('Intervention outside window')
        if digest(obs)!=before: raise ValueError('Feature input mutation')
        records.append({'step':step,'day':step//24,'candidate_callback_ms':cm,'reference_callback_ms':rm,'null_callback_ms':nm,
           'changed':ca!=ra,'farm_changed':(ca['farmer'],ca['hands'])!=(ra['farmer'],ra['hands']),
           'action':ca,'reference_action':ra,**features})
    return records


def identical_branch(control,screen_rows):
    if len(screen_rows)!=527 or [r['step'] for r in screen_rows]!=list(range(192,719)) or any(r['changed'] for r in screen_rows):
        raise ValueError('Full unchanged action sequence required for identity reuse')
    for r,old in zip(screen_rows,control['trace'],strict=True):
        if r['action']!=old['action'] or r['reference_action']!=old['action']:
            raise ValueError('Cannot certify counterfactual identity')
    result=deepcopy(control);result['mode']='clear_only';result['evidence_method']='full_control_path_action_identity_no_new_transitions'
    for r in result['trace']:
        r['mode']='clear_only';r['same_state_action_changed']=False
    result['new_transitions']=0
    return result


def rollout(payload,key,control,game,make_environment,layout,emit,log,actor_factory=make_actors):
    source=indexed_source(payload);seat=key['seat'];env=make_environment(key['seed'])
    if env.configuration.get('seed') is not None: raise ValueError('Seed leakage into actor configuration')
    for step in range(START):
        compare_source(observations(env),source,step)
        env.step([deepcopy(source[step,p]['action']) for p in (0,1)])
        if (step+1)%48==0:log('PREFIX_REPLAY',completed=step+1,total=START)
    current=observations(env);compare_source(current,source,START)
    initial=digest(current)
    if initial!=control['initial_sha256']: raise ValueError('Factorial branch initial state differs')
    c,r,n,rival=actor_factory(game,key,START);trace=[]
    for step in range(START,END+1):
        obs=observations(env)
        if clock(obs[seat])!=step: raise ValueError('Live clock drift')
        before=digest(obs[seat]);features=extract(obs[seat],game,layout)
        ca,cm=measure(c,obs[seat],'candidate',emit);ra,rm=measure(r,obs[seat],'same_state_control',emit)
        na,nm=measure(n,obs[seat],'same_state_null',emit);enemy,em=measure(rival,obs[1-seat],'opponent',emit)
        if ra!=na: raise ValueError('Null transformed policy differs')
        if not 8<=step//24<=27 and ca!=ra: raise ValueError('Intervention outside window')
        if digest(obs[seat])!=before:raise ValueError('Features mutated observation')
        commands=[ca['farmer'],*ca['hands']]
        row={'step':step,'day':step//24,'mode':'clear_only','own_cash_before':obs[seat]['farms'][seat]['money'],
             'candidate_callback_ms':cm,'reference_callback_ms':rm,'null_callback_ms':nm,'opponent_callback_ms':em,
             'same_state_action_changed':ca!=ra,'action':deepcopy(ca),'opponent_action':deepcopy(enemy),
             'reference_action':deepcopy(ra),'water_commands':sum(a[0]=='WATER' for a in commands),
             'dig_commands':sum(a[0]=='DIG' for a in commands),'plant_commands':sum(a[0]=='PLANT' for a in commands),
             'features':features}
        actions=[None,None];actions[seat]=ca;actions[1-seat]=enemy
        env.step(actions);nxt=observations(env)
        row.update(own_cash=float(nxt[seat]['farms'][seat]['money']),opponent_cash=float(nxt[seat]['farms'][1-seat]['money']))
        trace.append(row)
        if len(trace)%48==0: log('SUFFIX_PROGRESS',completed=len(trace),total=527)
    if len(env.steps)!=720 or any(s.status!='DONE' for s in env.state):raise ValueError('Incomplete terminal state')
    rewards=[float(s.reward) for s in env.state]
    if any(rewards[p]!=nxt[p]['farms'][p]['money'] for p in (0,1)):raise ValueError('Reward/cash mismatch')
    private=nxt[seat]['private'];residual=sum(q for inv in [private['shed'],*private['inventories']] for item,q in inv.items() if item in game.PRODUCTS)
    margin=rewards[seat]-rewards[1-seat]
    return {'key':key,'mode':'clear_only','initial_sha256':initial,'suffix_transitions':527,'null_action_checks':527,
       'prefix_replay_transitions':192,'new_transitions':719,'trace':trace,'final_state_sha256':digest(nxt),
       'evidence_method':'one_new_responsive_continuation',
       'metrics':{'coins':rewards[seat],'opponent_coins':rewards[1-seat],'coin_margin':margin,
          'local_match_score':float(margin>0)+.5*float(margin==0),'residual_product_units':residual}}
