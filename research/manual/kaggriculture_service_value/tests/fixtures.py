from copy import deepcopy
from types import SimpleNamespace
CROPS={
 'WHEAT':{'first_yield_day':2,'max_yield_day':4,'interval':0,'max_yield':6,'ongoing':False},
 'TOMATO':{'first_yield_day':8,'max_yield_day':8,'interval':1,'max_yield':4,'ongoing':True}}
ANIMALS={'GOOSE':{'first_yield_day':4,'interval':1,'max_held':4,'product':'EGG'},
 'COW':{'first_yield_day':8,'interval':2,'max_held':6,'product':'MILK'}}
GAME=SimpleNamespace(CROPS=CROPS,ANIMALS=ANIMALS,PRODUCTS=['WHEAT','TOMATO','EGG','MILK','FERTILIZER'],market_price=lambda item,inv:max(1,30-inv//10))
def observation(hour=12,day=10,seat=0,hands=1):
 def farm():return {'farmer':[0,0],'hands':[[4,4] for _ in range(hands)],'tiles':[[None for _ in range(10)] for _ in range(10)],'money':3000,'hires_today':hands,'unlocked_quadrants':['NW']}
 obs={'day':day,'hour':hour,'step':day*24+hour,'player':seat,'farms':[farm(),farm()],
      'private':{'shed':{p:0 for p in GAME.PRODUCTS},'seeds':{},'inventories':[{} for _ in range(hands+1)]},
      'market':{'prices':{p:30 for p in GAME.PRODUCTS},'inventory':{p:0 for p in GAME.PRODUCTS}},'town':{'unlocked_shops':[]}}
 obs['farms'][seat]['tiles'][4][4]=plant(day)
 return obs

def plant(day=10):return {'kind':'PLANT','crop':'WHEAT','planted_day':day-3,'yield_units':3,'watered_today':False,'consecutive_unwatered':1,'fertilized_until_day':-1,'max_lifespan_step':9999}
def animal(day=10):return {'kind':'PASTURE','animal':'COW','placed_day':day-8,'yield_units':3,'fed_today':False,'consecutive_unfed':1,'cared_today':False,'fertilizer_available':True,'pending_care_bonus':1}
def job(op='HARVEST',priority=100,target=(4,4)):return SimpleNamespace(command=(op,),priority=priority,target=target)
