"""Round 20: completion slack for immediately survival-critical maintenance.

No WATER/FEED job is removed. The policy's existing priority is multiplied by
N/(N-d) only for feasible, resource-supported, next-refresh survival-critical
jobs. This engineering rule is a hypothesis, not a theorem of optimal scheduling.
"""
from __future__ import annotations
from feature_common import clock,distance,validate,finish,future_events
FIELDS=(
 'travel_actions','service_actions','service_effort','hours_left','decisions_left',
 'deadline_callback_offset','completion_slack','deadline_exists','reachable_today',
 'survival_critical','dry_or_unfed_streak','already_serviced','wheat_required',
 'worker_wheat','shed_wheat','resource_available','next_production_scheduled',
 'nominal_next_yield','held_units','held_quote_value','production_capacity',
 'production_headroom','future_events_in_season','own_worker_count',
 'alternative_ready_workers','nearest_other_ready_travel','exclusive_ready_access',
 'urgency_multiplier','reference_denominator','candidate_denominator',
 'score_multiplier','eligible_critical_job')
STATE_FIELDS=(
 'task_options','unique_tasks','worker_count','critical_options','eligible_critical_options',
 'unreachable_options','resource_blocked_options','exclusive_access_options',
 'minimum_critical_slack','mean_critical_slack','mean_score_multiplier','max_score_multiplier')

def urgency(night,travel,critical,resource,deadline):
    if not 1<=night<=24 or travel<0:raise ValueError('Invalid maintenance clock')
    eligible=bool(critical and resource and deadline and travel+1<=night)
    return night/(night-travel) if eligible else 1.0

def describe(obs,game,worker,target,op,*,farm=None,private=None):
    step=clock(obs);farm=farm if farm is not None else validate(obs)
    private=private if private is not None else obs['private'];positions=[farm['farmer'],*farm['hands']]
    if len(private['inventories'])!=len(positions) or not 0<=worker<len(positions):raise ValueError('Worker/private alignment')
    x,y=target;tile=farm['tiles'][y][x];day=obs['day'];night=24-obs['hour']
    if not isinstance(tile,dict):raise ValueError('Maintenance requires visible tile')
    if op=='WATER' and tile.get('kind')=='PLANT':
        params=game.CROPS[tile['crop']];item=tile['crop'];done=bool(tile['watered_today']);streak=tile['consecutive_unwatered']
        offset=day+1-tile['planted_day']-params['first_yield_day']
        scheduled=bool(params['ongoing'] and offset>=0 and offset%params['interval']==0 and offset//params['interval']<params['max_yield'])
        nominal=(2 if tile.get('fertilized_until_day',-1)>=day else 1) if scheduled else 0
        cap=params['max_yield'];future=sum(day<tile['planted_day']+params['first_yield_day']+k*params['interval']<=29 for k in range(params['max_yield'])) if params['ongoing'] else 0
    elif op=='FEED' and tile.get('animal') in game.ANIMALS:
        params=game.ANIMALS[tile['animal']];item=params['product'];done=bool(tile['fed_today']);streak=tile['consecutive_unfed']
        offset=day+1-tile['placed_day']-params['first_yield_day'];scheduled=offset>=0 and offset%params['interval']==0
        nominal=(1+tile.get('pending_care_bonus',0)) if scheduled else 0;cap=params['max_held']
        future=sum(d>=tile['placed_day']+params['first_yield_day'] and (d-tile['placed_day']-params['first_yield_day'])%params['interval']==0 for d in range(day+1,30))
    else:raise ValueError('Operation/tile mismatch')
    d=distance(positions[worker],target);wheat=int(private['inventories'][worker].get('WHEAT',0))
    resource=op!='FEED' or wheat>0;critical=not done and streak>=1;deadline=day<29
    multiplier=urgency(night,d,critical,resource,deadline);ref=d+1;candidate=ref/multiplier
    alternatives=[distance(p,target) for i,p in enumerate(positions) if i!=worker and (op!='FEED' or private['inventories'][i].get('WHEAT',0)>0)]
    available=sum(x+1<=night for x in alternatives);q=tile.get('yield_units',0)
    values=dict(zip(FIELDS,[d,1,ref,night,719-step,night-1,night-ref,int(deadline),int(ref<=night),
       int(critical),streak,int(done),int(op=='FEED'),wheat,private['shed'].get('WHEAT',0),int(resource),
       int(scheduled),nominal,q,q*obs['market']['prices'][item],cap,max(0,cap-q),future,len(positions),available,
       min(alternatives,default=-1),int(available==0),multiplier,ref,candidate,multiplier,
       int(critical and resource and deadline and ref<=night)],strict=True))
    return finish(values,32)

def score(obs,game,farm,private,worker,position,job,travel):
    ref=job.priority/(1+travel)
    if obs['day']==29 or job.command[0] not in ('WATER','FEED'):return ref
    row=describe(obs,game,worker,job.target,job.command[0],farm=farm,private=private)
    return job.priority/row['candidate_denominator']

def extract(obs,game):
    farm=validate(obs);rows=[]
    for w in range(1+len(farm['hands'])):
        for y,line in enumerate(farm['tiles']):
            for x,t in enumerate(line):
                if not isinstance(t,dict):continue
                op='WATER' if t.get('kind')=='PLANT' and not t['watered_today'] else ('FEED' if t.get('animal') and not t['fed_today'] else None)
                if op is None:continue
                rows.append({'worker':w,'x':x,'y':y,'operation':op,'item':t.get('crop',t.get('animal')),
                             **describe(obs,game,w,(x,y),op)})
    critical=[r['completion_slack'] for r in rows if r['eligible_critical_job']];n=len(rows)
    ss={'task_options':n,'unique_tasks':len({(r['x'],r['y'],r['operation']) for r in rows}),
        'worker_count':1+len(farm['hands']),'critical_options':sum(r['survival_critical'] for r in rows),
        'eligible_critical_options':sum(r['eligible_critical_job'] for r in rows),
        'unreachable_options':sum(not r['reachable_today'] for r in rows),
        'resource_blocked_options':sum(not r['resource_available'] for r in rows),
        'exclusive_access_options':sum(r['exclusive_ready_access'] for r in rows),
        'minimum_critical_slack':min(critical,default=-1),'mean_critical_slack':sum(critical)/len(critical) if critical else -1,
        'mean_score_multiplier':sum(r['score_multiplier'] for r in rows)/max(1,n),
        'max_score_multiplier':max((r['score_multiplier'] for r in rows),default=1)}
    return rows,finish(ss,12)
