"""Current own-observation helpers. No reward, seed, future replay or opponent inventory."""
from __future__ import annotations
from copy import deepcopy
import math
END=718
SHED=((4,4),(4,5),(5,4),(5,5))

def integer(v,low=0):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or int(v)!=v or v<low:raise ValueError('Invalid integer')
    return int(v)
def clock(obs):
    d=integer(obs['day']);h=integer(obs['hour']);s=d*24+h
    if h>=24 or s>END or (obs.get('step') is not None and obs['step']!=s):raise ValueError('Invalid public clock')
    return s
def distance(a,b):
    for p in (a,b):
        if len(p)!=2 or any(integer(x)>9 for x in p):raise ValueError('Expected 10x10 position')
    return abs(a[0]-b[0])+abs(a[1]-b[1])
def shed_distance(p):return min(distance(p,s) for s in SHED)
def validate(obs):
    clock(obs)
    if obs['player'] not in (0,1) or len(obs['farms'])!=2:raise ValueError('Expected two farms')
    farm=obs['farms'][obs['player']]
    if len(farm['tiles'])!=10 or any(len(r)!=10 for r in farm['tiles']):raise ValueError('Expected 10x10 board')
    return farm
def future_events(tile,day,crops):
    p=crops[tile['crop']]
    if not p['ongoing']:return 0
    return sum(tile['planted_day']+p['first_yield_day']+k*p['interval']>day for k in range(p['max_yield']))
def decay_count(tile,start,end):
    """Decay after actions start..end-1; no refresh is included."""
    integer(start);integer(end)
    if end<start:raise ValueError('Backwards interval')
    m=int(tile['max_lifespan_step'])
    if m<0:return 0
    lo=max(start,m);lo+=(lo-m)%2
    return max(0,(end-1-lo)//2+1)
def decay_tile(tile,start,end):
    t=deepcopy(tile)
    if t.get('kind')!='PLANT':return t
    t['yield_units']-=decay_count(t,start,end)
    return {'kind':'WEED'} if t['yield_units']<0 or (decay_count(tile,start,end)>0 and t['yield_units']<=0) else t

def refresh(tile,day,crops):
    """Independent pure next-refresh projection, including finite production."""
    t=deepcopy(tile)
    if t.get('kind')!='PLANT':return t,0
    p=crops[t['crop']];wet=bool(t['watered_today'])
    t['consecutive_unwatered']=0 if wet else int(t['consecutive_unwatered'])+1
    t['watered_today']=False
    if t['consecutive_unwatered']>=2:return {'kind':'WEED'},0
    produced=0
    if p['ongoing']:
        n=day+1-t['planted_day']-p['first_yield_day']
        if n>=0 and n%p['interval']==0 and n//p['interval']+1<=p['max_yield']:
            inc=2 if wet and t.get('fertilized_until_day',-1)>=day else 1
            old=t['yield_units'];t['yield_units']=min(p['max_yield'],old+inc);produced=t['yield_units']-old
            if n//p['interval']+1==p['max_yield']:t['max_lifespan_step']=(day+2)*24
    return t,produced

def finish(values,n):
    if len(values)!=n or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in values.values()):raise ValueError('Feature schema/nonfinite value')
    return {k:float(v) for k,v in values.items()}
def plant_tasks(obs,game):
    farm=validate(obs)
    for w,pos in enumerate([farm['farmer'],*farm['hands']]):
        for y,row in enumerate(farm['tiles']):
            for x,t in enumerate(row):
                if isinstance(t,dict) and t.get('kind')=='PLANT' and t['crop'] in game.CROPS and t['yield_units']>0 and obs['day']-t['planted_day']>=game.CROPS[t['crop']]['first_yield_day']:
                    yield w,pos,(x,y),t
