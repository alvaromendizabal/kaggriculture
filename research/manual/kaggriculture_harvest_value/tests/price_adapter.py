"""Independent small pricing adapter for LOCAL tests, not the installed engine.

Default numeric parameters and formulas transcribed from the inspected official
Kaggriculture source. The live mechanics gate uses the actual installed functions.
This adapter does not model seasons, players, weeds, or stochastic shop unlocks.
"""
from copy import deepcopy
from math import sqrt,log
from types import SimpleNamespace
from helpers import CROPS
RAW={
'WHEAT':(25,400,'sqrt',.8,'log',.2),'CARROT':(35,450,'hinge',1.,'sqrt',.7),
'TOMATO':(60,200,'hinge',.4,'sqrt',.6),'STRAWBERRY':(120,100,'sqrt',.7,'linear',1.6),
'MELON':(250,300,'log',.2,'sq',3.6),'EGG':(50,332,'hinge',.4,'log',.2),
'MILK':(160,122,'sqrt',.6,'linear',1.6),'WOOL':(200,105,'log',.2,'sq',3.2),
'FERTILIZER':(100,200,'linear',.4,'linear',.4)}
PARAMS={i:dict(base=v[0],I0=10000,T=v[1],below_func=v[2],below_target=v[3],above_func=v[4],above_target=v[5]) for i,v in RAW.items()}
SHOPS={'PIZZA_SHOP':['MILK','TOMATO','WHEAT'],'ICE_CREAM_SHOP':['STRAWBERRY','MILK','WHEAT'],'YARN_STORE':['WOOL'],'BAKERY':['EGG','WHEAT']}

def shape(name,x,T):
    if name=='linear':return x
    if name=='sqrt':return sqrt(x)
    if name=='log':return log(1+x)
    if name=='sq':return x*x
    if name=='hinge':return x/T+8*max(0,x/T-1)**2
    raise ValueError(name)

def price(i,inv):
    p=PARAMS[i];side='below' if inv<p['I0'] else 'above';sign=1 if side=='below' else -1
    return max(1,int(round(p['base']+sign*p[side+'_target']*p['base']*shape(p[side+'_func'],abs(inv-p['I0']),p['T'])/shape(p[side+'_func'],p['T'],p['T']))))

def commit(op,item,quote,farm,private,market,cap):
    if op!='SELL' or private['shed'].get(item,0)<=0:return False
    private['shed'][item]-=1;farm['money']+=quote
    market['inventory'][item]+=int(quote>1)
    return True

def consume(env,state,step):
    root=state[0].observation
    if step%4==0:
        for shop in root.town['unlocked_shops']:
            for item in SHOPS[shop]:root.market['inventory'][item]-=2 if len(SHOPS[shop])==1 else 1
    if step%24==0:
        for i in PARAMS:
            if i!='FERTILIZER':root.market['inventory'][i]-=1

GAME=SimpleNamespace(PRODUCTS=list(PARAMS),MARKET_PARAMS=PARAMS,CROPS=CROPS,
ANIMALS={'GOOSE':{'product':'EGG'},'COW':{'product':'MILK'},'SHEEP':{'product':'WOOL'}},
SHOPS=SHOPS,TOWN_CENTER_PRODUCTS=[i for i in PARAMS if i!='FERTILIZER'],
market_price=price,_commit_unit=commit,_town_consume=consume,
_resolve_market_params=lambda over:{i:{**p,**(over or {}).get(i,{})} for i,p in PARAMS.items()})

def obs(day=20,hour=0):
    from helpers import observation,plant
    o=observation(day,hour,plant('TOMATO',planted=10,units=4))
    o['market']={'inventory':{i:10000 for i in PARAMS},'prices':{i:price(i,10000) for i in PARAMS}}
    o['private']['shed']={i:0 for i in PARAMS}
    return o
