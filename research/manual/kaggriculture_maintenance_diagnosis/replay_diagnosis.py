"""Evaluator-only deterministic reconstruction and instrumented accounting.

Recorded actions are replayed, never recomputed by a candidate policy. A separate
copy of each turn is instrumented with original engine function bodies. No engine
module is monkey-patched. Cash, crop phases, original cash trace and final state
must reconcile before a result is accepted. Rival private data stays here.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
from types import SimpleNamespace, FunctionType
from artifact_io import digest
from interaction_features import extract
START, END = 480, 718

def observations(env):
    root=env.state[0].observation
    return [{'player':p,'step':int(root.day)*24+int(root.hour),'day':int(root.day),'hour':int(root.hour),
      'farms':deepcopy(root.farms),'market':deepcopy(root.market),'town':deepcopy(root.town),
      'private':deepcopy(env.state[p].observation.private)} for p in (0,1)]

def index_source(payload):
    rows={}
    for r in payload['records']:
        o=r['observation']; s=int(o['day'])*24+int(o['hour']); k=(s,r['player'])
        if k in rows: raise ValueError('Duplicate source record')
        rows[k]=r
    if set(rows)!={(s,p) for s in range(719) for p in (0,1)}:
        raise ValueError('Incomplete source episode')
    return rows

def source_parity(actual, records, step):
    for p in (0,1):
        expected=records[step,p]['observation']
        for f in ('player','day','hour','farms','market','town','private'):
            if actual[p][f]!=expected[f]: raise ValueError(f'Prefix differs: step={step} seat={p} field={f}')

def is_plant(t):
    return isinstance(t,dict) and t.get('kind')=='PLANT'

def plant_unit_events(game, farm, private, unit, action, day, step):
    pos=game._farmer_position(farm,unit)
    if pos is None: raise ValueError('Unexpected action for nonexistent worker')
    x,y=pos; before=deepcopy(farm['tiles'][y][x]); inv_before=deepcopy(private['inventories'][unit])
    snapshot=digest((farm,private))
    game._apply_unit_action(farm,private,unit,action,10,day,24,100)
    after=farm['tiles'][y][x]; out=[]
    op=action[0] if isinstance(action,list) and action else 'INVALID'
    if is_plant(before) or is_plant(after):
        crop=before['crop'] if is_plant(before) else after['crop']
        cohort=before['planted_day'] if is_plant(before) else after['planted_day']
        base={'step':step,'day':day,'x':x,'y':y,'crop':crop,'planted_day':cohort,'unit':unit,'command':op,
          'effective':int(snapshot!=digest((farm,private)))}
        event=None; units=0
        if op=='WATER' and is_plant(before) and is_plant(after):
            event='water'; units=max(0,after['yield_units']-before['yield_units'])
        elif op=='HARVEST' and is_plant(before):
            event='harvest'; units=private['inventories'][unit].get(crop,0)-inv_before.get(crop,0)
        elif op=='PLANT' and not is_plant(before) and is_plant(after):
            event='plant'; units=after['yield_units']
        elif op=='DIG' and is_plant(before) and not is_plant(after):
            event='dig_removal'; units=before['yield_units']
        elif op=='FERTILIZE' and is_plant(before):
            event='fertilize'; units=0
        if event: out.append({**base,'event':event,'units':units})
    return out

def shadow_turn(current, actions, game, configuration, step):
    farms=deepcopy(current[0]['farms']); market=deepcopy(current[0]['market'])
    privates=[deepcopy(o['private']) for o in current]
    state=[SimpleNamespace(observation=SimpleNamespace(farms=farms,market=market,private=privates[p]),action=deepcopy(actions[p])) for p in (0,1)]
    events=[]; trades=[]
    # Match the engine's atomic seed check before any worker acts.
    for player in (0,1):
        a=actions[player]; cmds=[a.get('farmer',['PASS']),*a.get('hands',[])]
        demand=Counter(c[1] for c in cmds if isinstance(c,list) and len(c)>=2 and c[0]=='PLANT')
        blocked={c for c,n in demand.items() if n>privates[player]['seeds'].get(c,0)}
        for unit,cmd in enumerate(cmds):
            if unit>len(farms[player]['hands']): raise ValueError('Recorded excess hand command')
            if isinstance(cmd,list) and len(cmd)>=2 and cmd[0]=='PLANT' and cmd[1] in blocked: cmd=['PASS']
            for r in plant_unit_events(game,farms[player],privates[player],unit,cmd,step//24,step):
                events.append({'player':player,**r})
    namespace=dict(game._process_market.__globals__)
    players={id(f):p for p,f in enumerate(farms)}
    def commit(op,item,price,farm,private,mkt,shed_capacity=100):
        before=farm['money']
        ok=game._commit_unit(op,item,price,farm,private,mkt,shed_capacity)
        if ok:
            trades.append({'step':step,'day':step//24,'player':players[id(farm)],'operation':op,
              'item':item,'units':1,'cash':float(farm['money']-before)})
        return ok
    def hire(farm,private,board_size,mult):
        before=farm['money']; game._do_hire(farm,private,board_size,mult)
        if farm['money']!=before:
            trades.append({'step':step,'day':step//24,'player':players[id(farm)],'operation':'HIRE','item':'LABOR','units':1,'cash':float(farm['money']-before)})
    def land(farm,board_size):
        before=farm['money']; game._do_buy_land(farm,board_size)
        if farm['money']!=before:
            trades.append({'step':step,'day':step//24,'player':players[id(farm)],'operation':'BUY_LAND','item':'LAND','units':1,'cash':float(farm['money']-before)})
    namespace.update(_commit_unit=commit,_do_hire=hire,_do_buy_land=land)
    original=game._process_market
    instrumented=FunctionType(original.__code__,namespace,original.__name__,original.__defaults__,original.__closure__)
    instrumented(state,SimpleNamespace(configuration=configuration))
    for p in (0,1):
        delta=farms[p]['money']-current[0]['farms'][p]['money']
        if delta!=sum(r['cash'] for r in trades if r['player']==p):
            raise ValueError('Instrumented turn cash does not reconcile')
        before=deepcopy(farms[p]['tiles'])
        game._decay_plants(farms[p],step)
        for y,row in enumerate(before):
            for x,t in enumerate(row):
                if not is_plant(t): continue
                after=farms[p]['tiles'][y][x]
                lost=t['yield_units']-(after['yield_units'] if is_plant(after) else 0)
                if lost or not is_plant(after): events.append({'step':step,'day':step//24,'player':p,'x':x,'y':y,'crop':t['crop'],'planted_day':t['planted_day'],'unit':-1,'command':'DECAY','effective':1,'event':'decay_death' if not is_plant(after) else 'decay_loss','units':lost})
        if step%24==23:
            before=deepcopy(farms[p]['tiles']); game._daily_refresh_plants(farms[p],step//24,24)
            for y,row in enumerate(before):
                for x,t in enumerate(row):
                    if not is_plant(t): continue
                    after=farms[p]['tiles'][y][x]
                    base={'step':step,'day':step//24,'player':p,'x':x,'y':y,'crop':t['crop'],'planted_day':t['planted_day'],'unit':-1,'command':'REFRESH','effective':1}
                    if not is_plant(after): events.append({**base,'event':'dry_death','units':t['yield_units']}); continue
                    gain=after['yield_units']-t['yield_units']
                    if gain: events.append({**base,'event':'night_production','units':gain})
                    cp=game.CROPS[t['crop']]; offset=step//24+1-t['planted_day']-cp['first_yield_day']
                    due=cp['ongoing'] and offset>=0 and offset%cp['interval']==0 and offset//cp['interval']<cp['max_yield']
                    nominal=(2 if t['watered_today'] and t['fertilized_until_day']>=step//24 else 1) if due else 0
                    if nominal-gain>0: events.append({**base,'event':'production_capacity_block','units':nominal-gain})
    return farms,trades,events

def replay_branch(source, stream, environment, emit):
    """Replay exactly prior actions; no new decisions, interventions or rewards selected."""
    records=index_source(source); key=stream['key']; seat=key['seat']; saved=stream['checkpoint']; mode=saved['mode']
    env=environment.make_environment(key['seed'])
    for step in range(START):
        source_parity(observations(env),records,step)
        env.step([deepcopy(records[step,p]['action']) for p in (0,1)])
        if (step+1)%120==0: emit('PREFIX_REPLAY',mode=mode,completed=step+1,total=480)
    if digest(observations(env))!=saved['initial_sha256']: raise ValueError('Initial state hash differs')
    plants=[]; summaries=[]; trades=[]; events=[]; cash=[]; timings=[]
    import time
    initial_cash=[o['farms'][p]['money'] for p,o in enumerate(observations(env))]
    for record in stream['actions']:
        step=record['step']; current=observations(env)
        if current[seat]['step']!=step: raise ValueError('Clock drift')
        before=digest(current[seat]); tick=time.perf_counter()
        rows,summary=extract(current[seat],environment.game.CROPS)
        timings.append((time.perf_counter()-tick)*1000)
        if digest(current[seat])!=before: raise ValueError('Feature mutation')
        plants.extend({'mode':mode,'step':step,'day':step//24,**r} for r in rows)
        summaries.append({'mode':mode,'step':step,'day':step//24,**summary})
        shadow,tr,ev=shadow_turn(current,record['actions'],environment.game,env.configuration,step)
        env.step(deepcopy(record['actions'])); nxt=observations(env)
        expected=record['expected']
        if current[seat]['farms'][seat]['money']!=expected['own_cash_before'] or nxt[seat]['farms'][seat]['money']!=expected['own_cash'] or nxt[seat]['farms'][1-seat]['money']!=expected['opponent_cash']:
            raise ValueError(f'Recorded cash trace mismatch at {step}')
        for p in (0,1):
            actual=nxt[0]['farms'][p]
            if actual['money']!=shadow[p]['money']: raise ValueError('Shadow cash mismatch')
            # Random overnight weed spawning never changes a live crop. Check
            # every shadow live crop and every actual live crop in both directions.
            for y in range(10):
                for x in range(10):
                    a=actual['tiles'][y][x]; b=shadow[p]['tiles'][y][x]
                    if (is_plant(a) or is_plant(b)) and a!=b: raise ValueError('Crop phase accounting mismatch')
        trades.extend({'mode':mode,**r} for r in tr); events.extend({'mode':mode,**r} for r in ev)
        cash.append({'mode':mode,'step':step,'day':step//24,'own_cash':expected['own_cash'],'opponent_cash':expected['opponent_cash']})
        if (step-START+1)%48==0: emit('RECORDED_SUFFIX_REPLAY',mode=mode,completed=step-START+1,total=239)
    if len(env.steps)!=720 or [s.status for s in env.state]!=['DONE','DONE']:
        raise ValueError('Recorded replay incomplete')
    if digest(observations(env))!=saved['final_state_sha256']: raise ValueError('Final state hash differs from notebook12')
    rewards=[float(s.reward) for s in env.state]
    for p in (0,1):
        if rewards[p]-initial_cash[p]!=sum(r['cash'] for r in trades if r['player']==p):
            raise ValueError('Endpoint cash ledger failed')
    return {'mode':mode,'key':key,'plant_features':plants,'state_features':summaries,'trades':trades,
      'crop_events':events,'cash':cash,'feature_latency_ms':timings,'final_state_sha256':saved['final_state_sha256'],
      'initial_cash':initial_cash,'rewards':rewards,'recorded_trace_checks':239,'prefix_checks':480,
      'new_policy_calls':0,'new_interventions':0}
