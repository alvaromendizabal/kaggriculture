"""Round 17: value harvestable crop units at worker arrival, not at the current instant.

Only same-day arrival scenarios alter value. No future WATER, harvest, refresh,
price change, or rival trade is assumed. All other policy scores are unchanged.
"""
from feature_common import clock,distance,shed_distance,decay_count,future_events,finish,plant_tasks
FIELDS=(
'current_units','current_quote','current_quote_value','travel_actions','hours_until_refresh',
'same_day_arrival','arrival_callback','sale_callback_lower_bound','remaining_callbacks','delivery_actions',
'delivery_within_season','delivery_before_refresh','decay_on_route','units_at_arrival',
'lost_units_on_route','lost_quote_value','arrival_quote_value','survival_fraction','next_decay_offset',
'harvest_before_first_decay','arrival_slack_to_refresh','sale_slack_to_terminal','crop_age_days',
'ongoing_crop','future_production_events','watered_today','dry_streak','fertilized_today',
'own_shed_same_product','own_carried_same_product','own_shed_free','relative_value_reduction')
SUMMARY=('task_rows','same_day_task_rows','decay_exposed_rows','zero_at_arrival_rows','season_feasible_rows',
'current_worker_count','unique_ready_plants','max_travel','max_value_loss','mean_value_loss',
'fraction_decay_exposed','total_ready_units_unique')

def describe(obs,tile,target,position,game):
    step=clock(obs);p=game.CROPS[tile['crop']];q=int(tile['yield_units']);travel=distance(position,target)
    night=24-obs['hour'];same=travel<night;dc=decay_count(tile,step,step+travel) if same else 0
    remaining=max(0,q-dc) if same else q
    quote=obs['market']['prices'][tile['crop']];sale=step+travel+shed_distance(target)+1
    m=tile['max_lifespan_step'];offset=-1
    if m>=0:
        nxt=max(step,m);nxt+=(nxt-m)%2;offset=nxt-step
    private=obs['private'];shed=private['shed'];carried=sum(inv.get(tile['crop'],0) for inv in private['inventories'])
    vals=(q,quote,q*quote,travel,night,int(same),step+travel,sale,719-step,
          travel+shed_distance(target)+2,int(sale<=718),int(sale<step+night),dc,remaining,
          q-remaining,(q-remaining)*quote,remaining*quote,remaining/max(1,q),offset,
          int(offset<0 or travel<=offset),night-travel-1,718-sale,obs['day']-tile['planted_day'],
          int(p['ongoing']),future_events(tile,obs['day'],game.CROPS),int(tile['watered_today']),
          tile['consecutive_unwatered'],int(tile['fertilized_until_day']>=obs['day']),
          shed.get(tile['crop'],0),carried,max(0,100-sum(shed.values())),(q-remaining)/max(1,q))
    return finish(dict(zip(FIELDS,vals,strict=True)),32)
def adjusted_value(obs,tile,target,position,game):
    return describe(obs,tile,target,position,game)['arrival_quote_value']
def extract(obs,game):
    rows=[]
    for w,pos,xy,t in plant_tasks(obs,game):rows.append({'worker':w,'x':xy[0],'y':xy[1],'crop':t['crop'],**describe(obs,t,xy,pos,game)})
    unique={(r['x'],r['y']):r['current_units'] for r in rows};n=len(rows)
    loss=[r['lost_quote_value'] for r in rows];count=sum(r['lost_units_on_route']>0 for r in rows)
    s=dict(zip(SUMMARY,(n,sum(r['same_day_arrival'] for r in rows),count,sum(r['units_at_arrival']==0 for r in rows),
       sum(r['delivery_within_season'] for r in rows),1+len(obs['farms'][obs['player']]['hands']),len(unique),
       max((r['travel_actions'] for r in rows),default=0),max(loss,default=0),sum(loss)/max(1,n),count/max(1,n),sum(unique.values())),strict=True))
    return rows,finish(s,12)
