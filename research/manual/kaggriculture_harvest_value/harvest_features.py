"""Current-observation harvest values; conditional sale paths are not forecasts.

Policies use only marginal revenue after a hypothetical liquidation of currently
held shed stock. No future trades, evaluator seeds, rewards, or opponent private
inventory are accepted. Demand-only arrival scenarios are diagnostic candidates,
not inputs to this milestone's action-changing intervention.
"""
from __future__ import annotations
from math import isfinite

FIELDS = (
    'quantity', 'current_quote', 'shed_units_ahead', 'headline_value',
    'lot_value_without_backlog', 'marginal_value_after_shed',
    'within_lot_price_impact', 'backlog_price_impact', 'total_quote_overstatement',
    'marginal_to_headline_ratio', 'post_shed_quote', 'price_floor_units_in_lot',
    'known_shop_demand_per_event', 'nearest_worker_travel',
    'earliest_delivery_delay', 'delivery_scenario_available',
    'known_demand_before_delivery', 'demand_only_marginal_value',
    'demand_only_value_change',
)
SUMMARY_FIELDS = ('harvest_tasks', 'crop_tasks', 'animal_tasks', 'total_ready_units',
                  'tasks_with_quote_overstatement', 'maximum_quote_overstatement',
                  'maximum_backlog_impact', 'tasks_with_available_delivery_scenario')


def integer(value, name, lower=0):
    if type(value) is not int or value < lower:
        raise ValueError(f'{name} must be an integer >= {lower}')
    return value


def clock(obs):
    day=integer(obs['day'],'day');hour=integer(obs['hour'],'hour')
    step=day*24+hour
    if hour>23 or step>718: raise ValueError('Outside default decision horizon')
    if obs.get('step') is not None and (type(obs['step']) is not int or obs['step']!=step):
        raise ValueError('Conflicting observation clock')
    return step


def sale_path(game, item, inventory, quantity):
    """Exact one-sided sale at the default curve, including non-accumulating floor."""
    if item not in game.PRODUCTS: raise ValueError('Unknown product')
    if type(inventory) is not int: raise ValueError('Inventory must be integral; negative is legal')
    integer(quantity,'quantity')
    # Quantities here are bounded by observed shed and one harvest, never arbitrary orders.
    if quantity>1000: raise ValueError('Unexpected scenario quantity; do not silently truncate')
    total=0.0;floors=0
    for i in range(quantity):
        price=game.market_price(item,inventory)
        if not isfinite(price) or price<1: raise ValueError('Invalid market quote')
        if price==1:
            floors=quantity-i;total+=floors;break
        total+=price;inventory+=1
    return total,inventory,floors


def marginal_value(game,item,inventory,quantity,ahead):
    """Defined scenario: sell current same-product shed stock, then this lot.

    Cash from the existing stock is NOT counted as harvest value. This omits
    reserves, future competitor orders, transport/decay and intervening demand.
    """
    integer(ahead,'ahead')
    _,post,_=sale_path(game,item,inventory,ahead)
    return sale_path(game,item,post,quantity)[0]


def known_demand(game,shops,item,step,delay):
    """Current shops only, after market at steps step..step+delay-1."""
    integer(step,'step');integer(delay,'delay')
    if any(s not in game.SHOPS for s in shops): raise ValueError('Unknown public shop')
    per=sum((2 if len(game.SHOPS[s])==1 else 1) for s in shops if item in game.SHOPS[s])
    n4=(step+delay-1)//4-(step-1)//4
    n24=(step+delay-1)//24-(step-1)//24
    return per*n4+int(item in game.TOWN_CENTER_PRODUCTS)*n24


def position(p):
    if len(p)!=2 or any(type(v) is not int or not 0<=v<10 for v in p):
        raise ValueError('Invalid default-board position')
    return p


def task_features(obs,game,item,quantity,x,y):
    step=clock(obs);player=obs['player']
    if type(player) is not int or player not in (0,1) or len(obs['farms'])!=2:
        raise ValueError('Expected two public farms')
    if game._resolve_market_params(obs['market'].get('params'))!=game.MARKET_PARAMS:
        raise ValueError('Non-default market parameters')
    integer(quantity,'quantity');position((x,y))
    farm=obs['farms'][player];workers=[farm['farmer'],*farm['hands']]
    travel=min(abs(x-position(p)[0])+abs(y-p[1]) for p in workers)
    shed_distance=min(abs(x-a)+abs(y-b) for a,b in ((4,4),(4,5),(5,4),(5,5)))
    delay=travel+1+shed_distance  # HARVEST at +travel; DROP/SELL at +delay.
    available=step+delay<=718 and delay<24-obs['hour']
    inv=obs['market']['inventory'][item];quote=obs['market']['prices'][item]
    if quote!=game.market_price(item,inv): raise ValueError('Observed quote differs from pinned curve')
    ahead=integer(obs['private']['shed'].get(item,0),'shed units')
    if sum(obs['private']['shed'].values())>100: raise ValueError('Unexpected shed capacity')
    gross=quote*quantity;lot=sale_path(game,item,inv,quantity)[0]
    _,post,_=sale_path(game,item,inv,ahead)
    marginal,_,floors=sale_path(game,item,post,quantity)
    shops=obs['town']['unlocked_shops']
    d=known_demand(game,shops,item,step,delay) if available else 0
    arrival=marginal_value(game,item,inv-d,quantity,ahead) if available else 0
    vals=(quantity,quote,ahead,gross,lot,marginal,gross-lot,lot-marginal,
          gross-marginal,marginal/gross if gross else 0,game.market_price(item,post),floors,
          sum((2 if len(game.SHOPS[s])==1 else 1) for s in shops if item in game.SHOPS[s]),
          travel,delay,int(available),d,arrival,arrival-marginal if available else 0)
    out=dict(zip(FIELDS,map(float,vals),strict=True))
    if not all(isfinite(v) for v in out.values()): raise ValueError('Nonfinite feature')
    return out


def extract(obs,game):
    step=clock(obs);p=obs['player']
    if type(p) is not int or p not in (0,1) or len(obs['farms'])!=2:raise ValueError('Invalid player')
    farm=obs['farms'][p]
    if len(farm['tiles'])!=10 or any(len(r)!=10 for r in farm['tiles']):raise ValueError('Expected 10x10 board')
    rows=[]
    for y,row in enumerate(farm['tiles']):
        for x,t in enumerate(row):
            if not isinstance(t,dict) or t.get('yield_units',0)<=0:continue
            kind=None
            if t.get('animal') in game.ANIMALS:
                item=game.ANIMALS[t['animal']]['product'];kind='animal'
            elif t.get('kind')=='PLANT':
                item=t['crop'];params=game.CROPS[item];age=obs['day']-t['planted_day']
                if age<params['first_yield_day']:continue
                if not(params['ongoing'] or age>=params['max_yield_day'] or 719-step<=24):continue
                kind='crop'
            else:continue
            rows.append({'x':x,'y':y,'item':item,'kind':kind,**task_features(obs,game,item,t['yield_units'],x,y)})
    vals=(len(rows),sum(r['kind']=='crop' for r in rows),sum(r['kind']=='animal' for r in rows),
          sum(r['quantity'] for r in rows),sum(r['total_quote_overstatement']>0 for r in rows),
          max((r['total_quote_overstatement'] for r in rows),default=0),
          max((r['backlog_price_impact'] for r in rows),default=0),
          sum(r['delivery_scenario_available'] for r in rows))
    return rows,dict(zip(SUMMARY_FIELDS,map(float,vals),strict=True))
