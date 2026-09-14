"""Round 19: conditional collection-to-sale timing, not a price forecast.

Only current own state enters this interface. Existing priority numerators are
unchanged. Travel/collection/deposit geometry is exact in the default grid;
capacity, future decay, other jobs and competing trades make banking conditional.
"""
from __future__ import annotations
from feature_common import clock, distance, shed_distance, validate, finish

FIELDS = (
 'task_units','current_quote','quoted_goods_value','travel_actions',
 'collection_actions','return_actions','deposit_actions','collection_effort',
 'direct_delivery_effort','manual_sale_offset','night_sale_offset',
 'manual_sale_available','night_sale_available','earliest_sale_offset',
 'completion_denominator','reference_denominator','candidate_denominator',
 'score_multiplier','hours_left','decisions_left','arrival_today',
 'delivery_before_refresh','terminal_slack','shed_free','own_carried_units',
 'same_product_in_shed','own_worker_count','alternative_worker_count',
 'nearest_other_travel','exclusive_access','one_sided_liquidation',
 'conditional_value_per_callback')
STATE_FIELDS = ('task_options','unique_tasks','worker_count','collection_candidates',
 'night_delivery_options','manual_delivery_options','unavailable_options',
 'mean_completion_callbacks','mean_score_multiplier','min_score_multiplier',
 'positive_stock_options','capacity_stress_options')

def goods(tile,op,game,day):
    if op=='COLLECT_FERTILIZER':
        return ('FERTILIZER',int(bool(tile.get('animal') and tile.get('fertilizer_available'))))
    if op!='HARVEST':return ('',0)
    if tile.get('kind')=='PLANT':
        c=tile['crop'];ready=day-tile['planted_day']>=game.CROPS[c]['first_yield_day']
        return c,int(tile['yield_units']) if ready else 0
    if tile.get('animal') in game.ANIMALS:
        return game.ANIMALS[tile['animal']]['product'],int(tile['yield_units'])
    return ('',0)

def timing(step,travel,return_steps):
    """Offsets label the callback containing SELL, not the post-action state.

    HARVEST at offset d -> DROP/SELL at d+1+r. Overnight auto-deposit is
    after the market phase, hence SELL first becomes possible at offset N.
    A manual route crossing reset is not treated as valid without replanning.
    """
    if not 0<=step<=718 or travel<0 or return_steps<0:raise ValueError('Invalid timing input')
    night=24-step%24;left=719-step;manual=travel+1+return_steps
    arrive=travel+1<=night
    direct_ok=arrive and manual<night and manual<left
    night_ok=arrive and night<left
    choices=([manual] if direct_ok else [])+([night] if night_ok else [])
    offset=min(choices) if choices else -1
    denominator=offset+1 if choices else travel+1
    return night,left,manual,arrive,direct_ok,night_ok,offset,denominator

def describe(obs,game,worker,target,op,*,farm=None,private=None):
    step=clock(obs);farm=farm if farm is not None else validate(obs)
    private=private if private is not None else obs['private']
    positions=[farm['farmer'],*farm['hands']]
    if len(private['inventories'])!=len(positions) or not 0<=worker<len(positions):raise ValueError('Worker/private alignment')
    x,y=target;tile=farm['tiles'][y][x]
    if not isinstance(tile,dict):raise ValueError('Task requires a visible tile')
    item,q=goods(tile,op,game,obs['day'])
    if not item or q<=0:raise ValueError('Task has no currently collectable goods')
    d=distance(positions[worker],target);r=shed_distance(target)
    night,left,manual,arrival,mok,nok,offset,denom=timing(step,d,r)
    # This study changes no terminal-day score and keeps the native value for
    # unavailable, cross-reset scenarios. Unavailable is not a zero-value label.
    ref=d+1;candidate=denom if obs['day']<29 and offset>=0 else ref
    price=float(obs['market']['prices'][item]);inv=int(obs['market']['inventory'][item]);rev=0.0
    for _ in range(q):
        p=game.market_price(item,inv);rev+=p;inv+=int(p>1)
    others=[distance(p,target) for i,p in enumerate(positions) if i!=worker]
    alternate=sum(t+1<=night for t in others)
    free=max(0,100-sum(private['shed'].values()))
    values=dict(zip(FIELDS,[q,price,q*price,d,1,r,1,d+1,d+r+2,manual,night,
        int(mok),int(nok),offset,denom,ref,candidate,ref/candidate,night,left,
        int(arrival),int(mok),left-1-offset if offset>=0 else -1,free,
        sum(private['inventories'][worker].values()),private['shed'].get(item,0),
        len(positions),alternate,min(others,default=-1),int(alternate==0),rev,
        rev/(offset+1) if offset>=0 else 0],strict=True))
    return finish(values,32)

def score(obs,game,farm,private,worker,position,job,travel):
    reference=job.priority/(1+travel)
    if obs['day']==29 or job.command[0] not in ('HARVEST','COLLECT_FERTILIZER'):return reference
    row=describe(obs,game,worker,job.target,job.command[0],farm=farm,private=private)
    return job.priority/row['candidate_denominator']

def extract(obs,game):
    farm=validate(obs);rows=[]
    for w in range(1+len(farm['hands'])):
        for y,line in enumerate(farm['tiles']):
            for x,tile in enumerate(line):
                if not isinstance(tile,dict):continue
                for op in ('HARVEST','COLLECT_FERTILIZER'):
                    item,q=goods(tile,op,game,obs['day'])
                    if q<=0:continue
                    rows.append({'worker':w,'x':x,'y':y,'operation':op,'item':item,
                                 **describe(obs,game,w,(x,y),op)})
    n=len(rows);multipliers=[r['score_multiplier'] for r in rows]
    ss={'task_options':n,'unique_tasks':len({(r['x'],r['y'],r['operation']) for r in rows}),
        'worker_count':1+len(farm['hands']),'collection_candidates':sum(r['arrival_today'] for r in rows),
        'night_delivery_options':sum(r['night_sale_available'] for r in rows),
        'manual_delivery_options':sum(r['manual_sale_available'] for r in rows),
        'unavailable_options':sum(r['earliest_sale_offset']<0 for r in rows),
        'mean_completion_callbacks':sum(r['completion_denominator'] for r in rows)/max(1,n),
        'mean_score_multiplier':sum(multipliers)/max(1,n),'min_score_multiplier':min(multipliers,default=1),
        'positive_stock_options':n,'capacity_stress_options':sum(r['task_units']>r['shed_free'] for r in rows)}
    return rows,finish(ss,12)
