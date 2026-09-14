"""Prospective crop interactions, never future actions, rewards or rival private data.

Four conditional pathways: PASS/PASS, WATER/PASS, PASS/HARVEST, WATER/HARVEST.
Both commands occur on the same existing tile at current step and step+1.
No travel, subsequent harvest, fertilizer application, or later WATER is assumed.
These are local scenarios, not feasible joint plans or forecasts. Outcome ledgers
are generated in a separate evaluator and never enter this interface.
"""
from __future__ import annotations
from copy import deepcopy
from math import isfinite
from crop_dynamics import clock, validate_tile, water_now, next_refresh
FIELDS = (
 'scenario_available','pass_units','water_units','harvest_units','water_harvest_units',
 'water_gain_without_harvest','water_gain_with_harvest','water_harvest_interaction',
 'cap_masked_water_gain','two_refresh_available','no_water_alive_after_two',
 'water_now_alive_after_two','two_refresh_survival_buffer_gain',
 'current_water_deadline_callbacks','nearest_worker_travel','second_worker_travel',
 'single_worker_water_actions','current_water_deadline_slack','workers_with_water_access',
 'current_yield_headroom','fertilizer_active_next_refresh','next_refresh_available')
SUMMARY_FIELDS = ('crop_count','workers','urgent_water_tasks','deferred_dry_tasks',
                  'two_refresh_vulnerable_crops','cap_masked_water_crops',
                  'urgent_tasks_without_current_worker_access','urgent_tasks_per_worker')

def decay_one(t: dict, step: int) -> dict:
    t = deepcopy(t)
    if t.get('kind') != 'PLANT':
        return t
    life = t['max_lifespan_step']
    if life >= 0 and step >= life and (step-life) % 2 == 0:
        t['yield_units'] -= 1
        if t['yield_units'] <= 0:
            return {'kind':'WEED'}
    return t

def conditional_path(tile: dict, obs: dict, crops: dict, water: bool, harvest: bool) -> dict:
    step = clock(obs); day, hour = obs['day'], obs['hour']
    validate_tile(tile, day, crops)
    if day >= 29 or hour > 22:
        raise ValueError('Two same-day commands require an available refresh and hour <=22')
    t = water_now(tile, day, crops[tile['crop']]) if water else deepcopy(tile)
    t = decay_one(t, step)
    collected = 0
    if t.get('kind') == 'PLANT' and harvest:
        p = crops[t['crop']]
        if day - t['planted_day'] >= p['first_yield_day'] and t['yield_units'] > 0:
            collected = t['yield_units']
            if p['ongoing']:
                t['yield_units'] = 0
            else:
                t = None
    if isinstance(t,dict) and t.get('kind') == 'PLANT':
        t = next_refresh(t, day, hour+1, crops, water=False)
    return {'tile':t,'harvested':collected,'total_units':collected + (t.get('yield_units',0) if isinstance(t,dict) else 0)}

def plant_features(tile: dict, obs: dict, position: tuple, workers: list, crops: dict) -> dict:
    step = clock(obs); day, hour = obs['day'], obs['hour']
    validate_tile(tile, day, crops)
    if not workers:
        raise ValueError('At least the main farmer is required')
    x,y = position
    if any(len(p)!=2 or any(type(v) is not int or not 0<=v<10 for v in p) for p in [position,*workers]):
        raise ValueError('Invalid board coordinates')
    p=crops[tile['crop']]
    available = day<29 and hour<=22
    totals = [conditional_path(tile,obs,crops,w,h)['total_units'] for w,h in [(False,False),(True,False),(False,True),(True,True)]] if available else [0]*4
    no,water,harv,both = totals
    gain0,gain1 = water-no, both-harv
    two = day<=27
    alive2=[]
    if two:
        for w in (False,True):
            t=next_refresh(tile,day,hour,crops,water=w)
            if t.get('kind')=='PLANT':
                t=next_refresh(t,day+1,0,crops,water=False)
            alive2.append(int(t.get('kind')=='PLANT'))
    else:
        alive2=[0,0]
    distances=sorted(abs(x-a)+abs(y-b) for a,b in workers)
    # Deadline for current survival-only service. Harvest/dig before that would
    # change the obligation. Hands expire at night; never extrapolate them tomorrow.
    if tile['watered_today']:
        deadline=72-hour
    else:
        deadline=(24 if tile['consecutive_unwatered']>=1 else 48)-hour
    deadline=min(deadline,719-step)
    due_now=not tile['watered_today'] and tile['consecutive_unwatered']>=1
    service=distances[0]+1
    cap=p['max_yield']
    values=[int(available),*totals,gain0,gain1,gain1-gain0,
      int(available and gain0==0 and gain1>0),int(two),*alive2,alive2[1]-alive2[0],
      deadline,distances[0],distances[1] if len(distances)>1 else distances[0],
      service,deadline-service,sum(d+1<=min(24-hour,719-step) for d in distances),
      max(0,cap-tile['yield_units']),int(tile['fertilized_until_day']>=day),int(day<29)]
    out=dict(zip(FIELDS,map(float,values),strict=True))
    if not all(isfinite(x) for x in out.values()):
        raise ValueError('Non-finite feature')
    return out

def extract(observation: dict, crops: dict) -> tuple[list,dict]:
    """Read only own public farm, current clock, and fixed crop mechanics."""
    clock(observation)
    player=observation['player']
    if type(player) is not int or player not in (0,1) or len(observation['farms'])!=2:
        raise ValueError('Expected two public farms')
    farm=observation['farms'][player]
    workers=[farm['farmer'],*farm['hands']]
    if len(farm['tiles'])!=10 or any(len(row)!=10 for row in farm['tiles']):
        raise ValueError('Expected default 10x10 board')
    rows=[]
    for y,row in enumerate(farm['tiles']):
        for x,t in enumerate(row):
            if isinstance(t,dict) and t.get('kind')=='PLANT':
                rows.append({'x':x,'y':y,'crop':t['crop'],'planted_day':t['planted_day'],
                             'dry_streak':t['consecutive_unwatered'],
                             'watered_today':int(t['watered_today']),
                             **plant_features(t,observation,(x,y),workers,crops)})
    urgent=[r for r in rows if not r['watered_today'] and r['dry_streak']>=1]
    vals=[len(rows),len(workers),len(urgent),
      sum(not r['watered_today'] and r['dry_streak']==0 for r in rows),
      sum(r['two_refresh_survival_buffer_gain']>0 for r in rows),
      sum(r['cap_masked_water_gain'] for r in rows),
      sum(r['workers_with_water_access']==0 for r in urgent),len(urgent)/len(workers)]
    return rows,dict(zip(SUMMARY_FIELDS,map(float,vals),strict=True))
