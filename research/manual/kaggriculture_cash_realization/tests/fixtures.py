"""Small artificial rules/states for isolated tests; NOT the Kaggle engine."""
from copy import deepcopy
from types import SimpleNamespace

PRODUCTS=('WHEAT','CARROT','TOMATO','STRAWBERRY','MELON','EGG','MILK','WOOL','FERTILIZER')


def fixture(step=710,seat=0,hands=0):
    farms=[{'money':3000.,'farmer':[4,4],'hands':[[4,4] for _ in range(hands)],
            'hires_today':hands,'tiles':[[None]*10 for _ in range(10)],'unlocked_quadrants':['NW']} for _ in (0,1)]
    return {'step':step,'day':step//24,'hour':step%24,'player':seat,'farms':farms,
        'private':{'shed':{},'inventories':[{} for _ in range(hands+1)],'seeds':{}},
        'market':{'inventory':{i:10000 for i in PRODUCTS},'prices':{i:25 for i in PRODUCTS}},
        'town':{'unlocked_shops':[]}}


def price(item,inventory): return max(1,25-max(0,inventory-10000))
def value(obs,pos,tile): return {'net_scenario_value':tile.get('test_value',0)}


class ToyGame:
    PRODUCTS=PRODUCTS
    market_price=staticmethod(price)
    @staticmethod
    def _hire_cost(n):
        a,b=1,1
        for _ in range(n): a,b=b,a+b
        return a
    @staticmethod
    def _apply_unit_action(farm,private,index,action,*config):
        pos=farm['farmer'] if index==0 else farm['hands'][index-1]
        inv=private['inventories'][index]
        op=action[0]
        if op=='DROP' and tuple(pos) in ((4,4),(4,5),(5,4),(5,5)):
            for item,n in list(inv.items()):
                take=min(n,max(0,100-sum(private['shed'].values())))
                if take: private['shed'][item]=private['shed'].get(item,0)+take
                del inv[item]
        elif op=='PLANT':
            item=action[1]
            if private['seeds'].get(item,0)>0:
                private['seeds'][item]-=1
                farm['tiles'][pos[1]][pos[0]]={'kind':'PLANT','crop':item}
        elif op=='NORTH' and pos[1]>0: pos[1]-=1
    @staticmethod
    def interpreter(states,env):
        o=states[0].observation
        for i,s in enumerate(states):
            for w,a in enumerate([s.action['farmer'],*s.action['hands']]):
                ToyGame._apply_unit_action(o.farms[i],s.observation.private,w,a)
        # Sequential toy market is used only for harness-unit tests, not parity claims.
        for i,s in enumerate(states):
            for order in s.action['market']:
                if order[0]=='SELL':
                    _,item,n=order;private=s.observation.private
                    for _ in range(min(n,private['shed'].get(item,0))):
                        p=price(item,o.market['inventory'][item])
                        o.farms[i]['money']+=p;private['shed'][item]-=1
                        o.market['inventory'][item]+=int(p>1)
        for s in states:
            s.observation.day=(o.step+1)//24;s.observation.hour=(o.step+1)%24
            if o.step==718:s.status='DONE';s.reward=o.farms[s.observation.player]['money']
        return states
