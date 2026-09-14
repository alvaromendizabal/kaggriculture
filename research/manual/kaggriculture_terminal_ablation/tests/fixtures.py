"""Explicit synthetic test doubles. Never competition records or engine acceptance."""
from copy import deepcopy
from types import SimpleNamespace
from pathlib import Path
import sys
previous=Path(__file__).resolve().parents[2]/'kaggriculture_cash_realization'
if previous.is_dir(): sys.path.insert(0,str(previous))
from cash_features import extract_cash_features

PRODUCTS=['WHEAT','CARROT','TOMATO','STRAWBERRY','MELON','EGG','MILK','WOOL','FERTILIZER']

def price(item,supply): return 1 if supply>100000 else 10

def new_farm(size=10,money=3000):
    return {'money':float(money),'farmer':[4,4],'hands':[],
            'tiles':[[None]*10 for _ in range(10)],'unlocked_quadrants':['NW'],'hires_today':0}
def new_private(): return {'shed':{i:0 for i in PRODUCTS},'inventories':[{}],'seeds':{}}
def new_market(): return {'inventory':{i:10000 for i in PRODUCTS},'prices':{i:10 for i in PRODUCTS}}
def refresh(market): market['prices']={i:price(i,s) for i,s in market['inventory'].items()}
GAME=SimpleNamespace(PRODUCTS=PRODUCTS,market_price=price,_new_farm=new_farm,_new_private=new_private,
                     _new_market=new_market,_new_town=lambda:{'unlocked_shops':[]},_refresh_prices=refresh)

def observation(seat=0,step=696):
    return {'player':seat,'step':step,'day':step//24,'hour':step%24,
            'farms':[new_farm(),new_farm()],'private':new_private(),
            'market':new_market(),'town':{'unlocked_shops':[]}}

def transition(own,rival,action,rival_action,game=GAME):
    farms=deepcopy(own['farms']);market=deepcopy(own['market']);town=deepcopy(own['town'])
    priv=[None,None];actions=[None,None]
    for obs,act in ((own,action),(rival,rival_action)):
        priv[obs['player']]=deepcopy(obs['private']);actions[obs['player']]=deepcopy(act)
    for seat in (0,1):
        if actions[seat]['farmer']==['DROP']:
            for item,n in priv[seat]['inventories'][0].items():
                room=100-sum(priv[seat]['shed'].values());priv[seat]['shed'][item]+=min(room,n)
            priv[seat]['inventories'][0]={}
    for seat in (0,1):
        for order in actions[seat]['market']:
            if order[0]=='SELL':
                item,q=order[1:];q=min(q,priv[seat]['shed'][item]);priv[seat]['shed'][item]-=q
                for _ in range(q):
                    v=price(item,market['inventory'][item]);farms[seat]['money']+=v
                    market['inventory'][item]+=int(v>1)
    refresh(market)
    step=own['day']*24+own['hour']+1
    return [{'player':p,'day':step//24,'hour':step%24,'farms':deepcopy(farms),
             'market':deepcopy(market),'town':deepcopy(town),'private':priv[p],
             'status':'DONE' if step==719 else 'ACTIVE',
             'reward':farms[p]['money'] if step==719 else 0} for p in (0,1)]

class Candidate:
    def __init__(self,source_arm,variant,deposit=716):
        self.source_arm=source_arm;self.variant=variant;self.deposit=deposit;self.last_step=695
        self.last_diagnostics={}
    def __call__(self,obs):
        assert set(obs)=={'player','step','day','hour','farms','private','market','town'}
        assert obs['step']==self.last_step+1
        self.last_step=obs['step']
        post=deepcopy(obs['private']);drop=obs['step']==self.deposit
        if drop:
            for i,n in post['inventories'][0].items():post['shed'][i]+=n
            post['inventories'][0]={}
        before={i:n for i,n in obs['private']['shed'].items() if n}
        after={i:n for i,n in post['shed'].items() if n}
        control_orders=[['SELL',i,n] for i,n in sorted((after if self.source_arm=='sequential' else before).items())]
        aligned_orders=[['SELL',i,n] for i,n in sorted(after.items())]
        control={'farmer':['DROP'] if drop else ['PASS'],'hands':[],'market':control_orders}
        aligned={**deepcopy(control),'market':aligned_orders}
        features=extract_cash_features(obs,post,control_orders,aligned_orders,PRODUCTS,price)
        self.last_diagnostics={'active':True,'base_rule_parity':True,'control_action':control,'features':features.values}
        return deepcopy(control if self.variant=='control' else aligned)

class Rival:
    def __init__(self): self.last_step=695
    def __call__(self,obs):
        assert set(obs)=={'player','step','day','hour','farms','private','market','town'}
        assert obs['step']==self.last_step+1
        self.last_step=obs['step']
        orders=[]
        if obs['farms'][1-obs['player']]['money']>3000:
            n=obs['private']['shed']['WHEAT']
            if n:orders=[['SELL','WHEAT',n]]
        return {'farmer':['PASS'],'hands':[],'market':orders}

def factory(deposit=716):
    def make(source,variant,seat):return Candidate(source,variant,deposit),Rival(),Candidate(source,'control',deposit)
    return make

def make_payload(seat=0,source='coordinated',deposit=716,seed=1601):
    from continuation import legal_observation
    views=[observation(p) for p in (0,1)]
    views[seat]['private']['inventories'][0]={'WHEAT':2}
    views[1-seat]['private']['shed']['WHEAT']=1
    actor,rival,_=factory(deposit)(source,'control',seat)
    rows=[]
    for step in range(696,719):
        a=actor(deepcopy(views[seat]));b=rival(deepcopy(views[1-seat]))
        rows.extend([{'player':seat,'observation':deepcopy(views[seat]),'action':a},
                     {'player':1-seat,'observation':deepcopy(views[1-seat]),'action':b}])
        result=transition(views[seat],views[1-seat],a,b)
        if step<718:views=[legal_observation(x) for x in result]
    key={'seed':seed,'seat':seat,'opponent':'livestock_fertilizer','arm':source}
    return {'records':rows,'rewards':[x['reward'] for x in result], 'preterminal_sha256':'synthetic-prefix'},key
