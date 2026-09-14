"""Round 18: production headroom released by a same-day harvest.

Defined paths: current observation -> travel with no other actions -> optional
HARVEST -> remaining decay -> next refresh. Current watering is held fixed.
The difference is conditional production, not guaranteed future sales/profit.
"""
from copy import deepcopy
from feature_common import clock,distance,shed_distance,decay_tile,refresh,future_events,finish,plant_tasks
FIELDS=(
'current_units','current_quote','current_quote_value','current_headroom','crop_capacity',
'crop_age_days','ongoing_crop','future_production_events','travel_actions','hours_until_refresh',
'same_day_arrival','next_refresh_exists','scenario_available','next_production_scheduled',
'watered_today','dry_streak','fertilized_today','nominal_next_production',
'units_at_arrival','units_before_refresh_hold','units_before_refresh_harvest',
'survives_hold','survives_harvest','produced_hold','produced_harvest',
'released_production_units','released_quote_value','augmented_harvest_value',
'relative_headroom_bonus','own_shed_same_product','own_shed_free','delivery_slack')
SUMMARY=('task_rows','scenario_available_rows','blocked_production_rows','positive_release_rows',
'current_worker_count','unique_ready_plants','max_release_units','max_release_value',
'mean_release_value','fraction_positive_release','full_crop_rows','survival_risk_rows')

def paths(obs,tile,travel,game):
    s=clock(obs);night=24-obs['hour'];p=game.CROPS[tile['crop']]
    available=bool(p['ongoing'] and travel<night and s+night<=718)
    if not available:return {'available':False,'arrival':tile['yield_units'],'before_hold':0,'before_harvest':0,'hold_alive':0,'harvest_alive':0,'hold_produced':0,'harvest_produced':0,'release':0}
    a=decay_tile(tile,s,s+travel)
    ready=a.get('kind')=='PLANT' and a.get('yield_units',0)>0
    h=deepcopy(a)
    if ready:h['yield_units']=0
    bh=decay_tile(a,s+travel,s+night);bc=decay_tile(h,s+travel,s+night)
    ah,ph=refresh(bh,obs['day'],game.CROPS);ac,pc=refresh(bc,obs['day'],game.CROPS)
    return {'available':True,'arrival':a.get('yield_units',0),'before_hold':bh.get('yield_units',0),
       'before_harvest':bc.get('yield_units',0),'hold_alive':int(ah.get('kind')=='PLANT'),
       'harvest_alive':int(ac.get('kind')=='PLANT'),'hold_produced':ph,'harvest_produced':pc,
       'release':max(0,pc-ph) if ready else 0}
def describe(obs,tile,target,position,game):
    step=clock(obs);p=game.CROPS[tile['crop']];travel=distance(position,target);r=paths(obs,tile,travel,game)
    age=obs['day']-tile['planted_day'];offset=age+1-p['first_yield_day']
    due=bool(p['ongoing'] and offset>=0 and offset%p['interval']==0 and offset//p['interval']<p['max_yield'])
    wet=bool(tile['watered_today']);fert=tile['fertilized_until_day']>=obs['day'];q=tile['yield_units'];price=obs['market']['prices'][tile['crop']]
    value=q*price;extra=r['release']*price;shed=obs['private']['shed'];night=24-obs['hour']
    vals=(q,price,value,max(0,p['max_yield']-q),p['max_yield'],age,int(p['ongoing']),future_events(tile,obs['day'],game.CROPS),
       travel,night,int(travel<night),int(step+night<=718),int(r['available']),int(due),int(wet),tile['consecutive_unwatered'],int(fert),
       (2 if wet and fert else 1) if due else 0,r['arrival'],r['before_hold'],r['before_harvest'],r['hold_alive'],r['harvest_alive'],
       r['hold_produced'],r['harvest_produced'],r['release'],extra,value+extra,extra/max(1,value),shed.get(tile['crop'],0),
       max(0,100-sum(shed.values())),718-(step+travel+shed_distance(target)+1))
    return finish(dict(zip(FIELDS,vals,strict=True)),32)
def adjusted_value(obs,tile,target,position,game):return describe(obs,tile,target,position,game)['augmented_harvest_value']
def extract(obs,game):
    rows=[]
    for w,pos,xy,t in plant_tasks(obs,game):rows.append({'worker':w,'x':xy[0],'y':xy[1],'crop':t['crop'],**describe(obs,t,xy,pos,game)})
    n=len(rows);v=[r['released_quote_value'] for r in rows];pos=sum(r['released_production_units']>0 for r in rows)
    s=dict(zip(SUMMARY,(n,sum(r['scenario_available'] for r in rows),sum(r['scenario_available'] and r['survives_hold'] and r['produced_hold']<r['nominal_next_production'] for r in rows),
       pos,1+len(obs['farms'][obs['player']]['hands']),len({(r['x'],r['y']) for r in rows}),
       max((r['released_production_units'] for r in rows),default=0),max(v,default=0),sum(v)/max(1,n),pos/max(1,n),
       sum(r['current_headroom']==0 for r in rows),sum(r['scenario_available'] and not r['survives_hold'] for r in rows)),strict=True))
    return rows,finish(s,12)
