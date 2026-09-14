from copy import deepcopy
from types import SimpleNamespace
CROPS={
 'WHEAT':{'seed':10,'first_yield_day':2,'max_yield_day':4,'interval':0,'max_yield':6,'ongoing':False},
 'CARROT':{'seed':20,'first_yield_day':2,'max_yield_day':3,'interval':0,'max_yield':4,'ongoing':False},
 'TOMATO':{'seed':50,'first_yield_day':8,'max_yield_day':8,'interval':1,'max_yield':4,'ongoing':True},
 'STRAWBERRY':{'seed':100,'first_yield_day':10,'max_yield_day':10,'interval':2,'max_yield':4,'ongoing':True},
 'MELON':{'seed':80,'first_yield_day':10,'max_yield_day':12,'interval':0,'max_yield':6,'ongoing':False}}

def tile(crop='TOMATO',**kwargs):
    t={'kind':'PLANT','crop':crop,'planted_day':12,'watered_today':False,'consecutive_unwatered':0,
       'yield_units':4,'max_lifespan_step':-1,'fertilized_until_day':20};t.update(kwargs);return t

def farm():
    return {'money':3000.,'tiles':[[None]*10 for _ in range(10)],'farmer':[1,1],'hands':[],
      'unlocked_quadrants':['NW'],'hires_today':0}
def private(): return {'shed':{'WHEAT':3},'seeds':{},'inventories':[{}]}
def observation(day=20,hour=0,player=0):
    farms=[farm(),farm()];farms[player]['tiles'][1][1]=tile()
    return {'day':day,'hour':hour,'step':day*24+hour,'player':player,'farms':farms,
      'market':{'inventory':{'WHEAT':10000},'prices':{'WHEAT':25}},'private':private(),'town':{'unlocked_shops':[]}}

# Independent, small test adapter. It is not presented as the installed engine.
def component_path(t,day,hour,crops,water=False,harvest=False):
    t=deepcopy(t);collected=0
    for step in range(day*24+hour,day*24+24):
        if isinstance(t,dict) and t.get('kind')=='PLANT':
            p=crops[t['crop']]
            if water and step==day*24+hour and not t['watered_today']:
                t['watered_today']=True;age=day-t['planted_day']
                if not p['ongoing'] and (p['max_yield_day']+1)//2<=age<=p['max_yield_day']:
                    t['yield_units']=min(p['max_yield'],t['yield_units']+(2 if t['fertilized_until_day']>=day else 1))
            if harvest and step==day*24+hour+1 and day-t['planted_day']>=p['first_yield_day'] and t['yield_units']>0:
                collected=t['yield_units']; t['yield_units']=0
                if not p['ongoing']: t=None
        if isinstance(t,dict) and t.get('kind')=='PLANT':
            m=t['max_lifespan_step']
            if m>=0 and step>=m and (step-m)%2==0:
                t['yield_units']-=1
                if t['yield_units']<=0:t={'kind':'WEED'}
    if isinstance(t,dict) and t.get('kind')=='PLANT':
        p=crops[t['crop']]; w=t['watered_today'];t['consecutive_unwatered']=0 if w else t['consecutive_unwatered']+1;t['watered_today']=False
        if t['consecutive_unwatered']>=2:t={'kind':'WEED'}
        elif p['ongoing']:
            delta=day+1-t['planted_day']-p['first_yield_day']
            if delta>=0 and delta%p['interval']==0 and delta//p['interval']+1<=p['max_yield']:
                t['yield_units']=min(p['max_yield'],t['yield_units']+(2 if w and t['fertilized_until_day']>=day else 1))
                if delta//p['interval']+1==p['max_yield']:t['max_lifespan_step']=(day+2)*24
    return {'tile':t,'harvested':collected,'total_units':collected+(t.get('yield_units',0) if isinstance(t,dict) else 0)}

def toy_game():
    ns={}
    exec('''
def _commit_unit(op,item,price,farm,private,market,cap=100):
    if op=='SELL' and private['shed'].get(item,0)>0:
        private['shed'][item]-=1;farm['money']+=price;market['inventory'][item]+=1;return True
    if op=='BUY_SEED' and farm['money']>=price:
        farm['money']-=price;private['seeds'][item]=private['seeds'].get(item,0)+1;return True
    return False

def _do_hire(farm,private,size,mult):
    if farm['money']>=mult:
        farm['money']-=mult;farm['hands'].append([1,1]);private['inventories'].append({})
def _do_buy_land(farm,size):
    if farm['money']>=1000: farm['money']-=1000

def _process_market(state,env):
    for p,s in enumerate(state):
        f=s.observation.farms[p]
        for order in s.action.get('market',[]):
            op=order[0]
            if op=='HIRE': _do_hire(f,s.observation.private,10,1)
            elif op=='BUY_LAND': _do_buy_land(f,10)
            else:
                for _ in range(order[2]):
                    if not _commit_unit(op,order[1],5,f,s.observation.private,s.observation.market,100):break
''',ns)
    g=SimpleNamespace(**{n:v for n,v in ns.items() if n.startswith('_')},CROPS=CROPS)
    g._farmer_position=lambda f,i:f['farmer'] if i==0 else f['hands'][i-1] if i<=len(f['hands']) else None
    g._apply_unit_action=lambda *a:None
    g._decay_plants=lambda *a:None
    g._daily_refresh_plants=lambda *a:None
    return g
