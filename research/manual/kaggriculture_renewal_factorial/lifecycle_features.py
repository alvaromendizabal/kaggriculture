"""Observation-only productive-lifetime features, not future outcome predictors.

Scheduled events are conditional on a plant surviving. They are not a guarantee
of output, collection, delivery, sale price, or net profit. Opponent/private state,
recorded actions, evaluator seed and rewards are not read by these functions.
"""
from __future__ import annotations
from math import isfinite

ACTIVE_DAYS = tuple(range(8, 28))
FIELDS = (
    'ongoing', 'age_days', 'held_units', 'harvestable_units', 'watered_today',
    'dry_streak', 'fertilizer_active', 'first_production_day', 'last_production_day',
    'lifetime_event_count', 'scheduled_events_elapsed', 'scheduled_events_remaining',
    'events_before_game_end', 'has_future_event', 'callbacks_to_next_event',
    'empty_exhausted', 'water_job_redundant_by_lifetime',
    'main_farmer_travel', 'nearest_current_worker_travel',
    'next_decay_in_callbacks', 'decay_scheduled', 'frozen_replant_window_open',
    'renewal_eligible', 'replacement_seed_available', 'replacement_seed_cost',
    'replacement_first_sale_step_lower_bound', 'replacement_sale_horizon_feasible',
)
SUMMARY_FIELDS = ('plants', 'ongoing_plants', 'empty_exhausted_plants',
    'redundant_water_jobs', 'renewal_eligible_plots', 'scheduled_future_events',
    'mature_units_held', 'current_workers')


def integer(x, name, lo=0):
    if type(x) is not int or x < lo:
        raise ValueError(f'{name} must be an integer >= {lo}')
    return x


def clock(obs):
    day=integer(obs['day'],'day');hour=integer(obs['hour'],'hour')
    step=24*day+hour
    if hour>23 or step>718:raise ValueError('Outside pinned decision horizon')
    if obs.get('step') is not None and (type(obs['step']) is not int or obs['step']!=step):
        raise ValueError('Conflicting public clock')
    return step


def schedule(tile, crops):
    """All nominal production-event days; single-yield crops have no refresh events."""
    if not isinstance(tile,dict) or tile.get('kind')!='PLANT' or tile.get('crop') not in crops:
        raise ValueError('Expected a known plant')
    planted=integer(tile['planted_day'],'planted_day');p=crops[tile['crop']]
    integer(tile['yield_units'],'yield_units')
    if not p['ongoing']:return ()
    interval=integer(p['interval'],'interval',1)
    count=integer(p['max_yield'],'max_yield',1)
    return tuple(planted+p['first_yield_day']+i*interval for i in range(count))


def exhausted_empty(tile, obs, crops):
    """Stricter than notebook12: no held yield AND no remaining lifetime event.

    This never suppresses maintenance just because the next refresh is quiet,
    and never clears plants that still contain goods. No season-return claim.
    """
    clock(obs)
    if not isinstance(tile,dict) or tile.get('kind')!='PLANT':return False
    events=schedule(tile,crops)
    if tile['planted_day']>obs['day']:raise ValueError('Plant is from the future')
    return bool(events and events[-1]<=obs['day'] and tile['yield_units']==0)


def distance(a,b):
    for p in (a,b):
        if len(p)!=2 or any(type(v) is not int or not 0<=v<10 for v in p):
            raise ValueError('Invalid default-board position')
    return abs(a[0]-b[0])+abs(a[1]-b[1])


def plant_features(tile, obs, crops, x, y, layout):
    step=clock(obs);p=crops[tile['crop']];events=schedule(tile,crops)
    if tile['planted_day']>obs['day']:raise ValueError('Plant is from the future')
    age=obs['day']-tile['planted_day'];future=[d for d in events if d>obs['day']]
    owner=obs['player']
    if type(owner) is not int or owner not in (0,1) or len(obs['farms'])!=2:
        raise ValueError('Invalid public farms')
    farm=obs['farms'][owner];pos=(x,y)
    main=distance(farm['farmer'],pos)
    nearest=min(distance(w,pos) for w in [farm['farmer'],*farm['hands']])
    empty=exhausted_empty(tile,obs,crops)
    replacement=layout.get(pos)
    rp=crops[replacement] if replacement else None
    window=bool(rp and 719-step>rp['first_yield_day']*24+12)
    # Diagnostic lower bound only: farmer travels, DIGs, then PLANTs. Water,
    # crop death/decay, capacity, competing jobs and market responses are omitted.
    plant_step=step+main+1
    first_sale=(plant_step//24+rp['first_yield_day'])*24+min(distance(pos,s) for s in ((4,4),(4,5),(5,4),(5,5)))+1 if rp else 0
    mls=tile.get('max_lifespan_step',-1)
    integer(mls,'max_lifespan_step',-1)
    decay=-1
    if mls>=0:
        decay=max(step,mls)
        if (decay-mls)%2:decay+=1
    vals=(int(p['ongoing']),age,tile['yield_units'],tile['yield_units'] if age>=p['first_yield_day'] else 0,
          int(tile['watered_today']),integer(tile['consecutive_unwatered'],'dry_streak'),
          int(tile.get('fertilized_until_day',-1)>=obs['day']),
          events[0] if events else tile['planted_day']+p['first_yield_day'],
          events[-1] if events else tile['planted_day']+p['max_yield_day'],len(events),
          sum(d<=obs['day'] for d in events),len(future),sum(d<=29 for d in future),
          int(bool(future)),future[0]*24-step if future else 0,int(empty),
          int(empty and not tile['watered_today']),main,nearest,
          decay-step if decay>=0 else 0,int(decay>=0),int(window),int(empty and window),
          int(bool(replacement) and obs['private']['seeds'].get(replacement,0)>0),
          rp['seed'] if rp else 0,first_sale,int(bool(rp) and first_sale<=718))
    out=dict(zip(FIELDS,map(float,vals),strict=True))
    if not all(isfinite(v) for v in out.values()):raise ValueError('Nonfinite feature')
    return out


def extract(obs, game, layout):
    clock(obs);owner=obs['player']
    if type(owner) is not int or owner not in (0,1) or len(obs['farms'])!=2:
        raise ValueError('Invalid public farms')
    farm=obs['farms'][owner]
    if len(farm['tiles'])!=10 or any(len(r)!=10 for r in farm['tiles']):raise ValueError('Expected default board')
    rows=[]
    for y,row in enumerate(farm['tiles']):
        for x,t in enumerate(row):
            if isinstance(t,dict) and t.get('kind')=='PLANT':
                rows.append({'x':x,'y':y,'crop':t['crop'],'planted_day':t['planted_day'],
                    **plant_features(t,obs,game.CROPS,x,y,layout)})
    values=(len(rows),sum(r['ongoing'] for r in rows),sum(r['empty_exhausted'] for r in rows),
        sum(r['water_job_redundant_by_lifetime'] for r in rows),sum(r['renewal_eligible'] for r in rows),
        sum(r['scheduled_events_remaining'] for r in rows),sum(r['harvestable_units'] for r in rows),1+len(farm['hands']))
    return rows,dict(zip(SUMMARY_FIELDS,map(float,values),strict=True))
