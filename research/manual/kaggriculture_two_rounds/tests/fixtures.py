"""Explicit artificial observations plus attributed official component oracles."""
from copy import deepcopy
from types import SimpleNamespace
from tests.official_refresh_excerpt import CROPS,_daily_refresh_plants
from mechanics import farm

def _decay_plants(farm,step):
    # Kaggle kaggriculture.py public source, same pinned blob as refresh excerpt.
    for row in farm['tiles']:
        for i,t in enumerate(row):
            if not isinstance(t,dict) or t.get('kind')!='PLANT':continue
            m=t['max_lifespan_step']
            if m<0 or step<m or (step-m)%2:continue
            t['yield_units']-=1
            if t['yield_units']<=0:row[i]={'kind':'WEED'}
def _apply_unit_action(farm,private,index,action,board_size,day,turns_per_day,capacity):
    # Minimal artificial HARVEST adapter. This is NOT a full engine.
    pos=farm['farmer'] if index==0 else farm['hands'][index-1];x,y=pos;t=farm['tiles'][y][x]
    if action==['HARVEST'] and isinstance(t,dict) and t.get('kind')=='PLANT' and t['yield_units']>0 and day-t['planted_day']>=CROPS[t['crop']]['first_yield_day']:
        private['inventories'][index][t['crop']]=private['inventories'][index].get(t['crop'],0)+t['yield_units']
        t['yield_units']=0
        if not CROPS[t['crop']]['ongoing']:farm['tiles'][y][x]=None
GAME=SimpleNamespace(CROPS=CROPS,PRODUCTS=list(CROPS),_decay_plants=_decay_plants,_daily_refresh_plants=_daily_refresh_plants,_apply_unit_action=_apply_unit_action)

def obs(crop='TOMATO',day=10,hour=4,units=4,travel=0,expiry=-1,wet=True,streak=0,fert=False):
    p=CROPS[crop]
    t={'kind':'PLANT','crop':crop,'planted_day':day-p['first_yield_day'],'watered_today':wet,'consecutive_unwatered':streak,
      'yield_units':units,'fertilized_until_day':day if fert else -1,'max_lifespan_step':expiry}
    if crop=='STRAWBERRY':t['planted_day']-=1
    own=farm(t);own['farmer']=[4-travel,4];other=farm({'kind':'WEED'})
    return {'player':0,'step':day*24+hour,'day':day,'hour':hour,'farms':[own,other],
      'market':{'prices':{c:50 for c in CROPS},'inventory':{c:10000 for c in CROPS}},'town':{'unlocked_shops':[]},
      'private':{'shed':{c:0 for c in CROPS},'seeds':{c:0 for c in CROPS},'inventories':[{}]}}
def tile(o):return o['farms'][o['player']]['tiles'][4][4]
def desc(module,o):return module.describe(o,tile(o),(4,4),o['farms'][o['player']]['farmer'],GAME)
SOURCE='''def __call__(self,obs):
    tile=obs['tile'];position=obs['position'];target=obs['target']
    water=not tile['watered_today']
    value=tile['yield_units'] * obs['market']['prices'][tile['crop']]
    return value,water
'''
class ToyEnv:
    """719-step public-clock adapter used ONLY for driver control-flow tests."""
    def __init__(self):
        self.configuration={};self.steps=[0];self.t=0;self.state=[];self.money=[100.,100.];self.update()
    def update(self):
        from types import SimpleNamespace as S
        base=obs(day=min(29,self.t//24),hour=self.t%24,units=0)
        for p in (0,1):base['farms'][p]['money']=self.money[p]
        root=S(day=self.t//24,hour=self.t%24,farms=base['farms'],market=base['market'],town=base['town'])
        self.state=[S(observation=S(**vars(root),private=deepcopy(base['private'])),status='DONE' if self.t==719 else 'ACTIVE',reward=self.money[p] if self.t==719 else None) for p in (0,1)]
    def step(self,actions):
        for p,a in enumerate(actions):self.money[p]+=len(a['market'])
        self.t+=1;self.steps.append(self.t);self.update()
def pass_action(o):return {'farmer':['PASS'],'hands':[['PASS'] for _ in o['farms'][o['player']]['hands']],'market':[]}
def toy_factory(game,rid,mode,opp):
    def candidate(o):
        a=pass_action(o)
        if mode=='candidate' and o['step']==1:a['market']=[['SELL','WHEAT',1]]
        return a
    return candidate,pass_action,pass_action,pass_action
