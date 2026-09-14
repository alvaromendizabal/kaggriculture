"""Explicit artificial routing and trajectory fixtures; not an official engine."""
from dataclasses import dataclass
from itertools import product
from types import SimpleNamespace
from copy import deepcopy

@dataclass(frozen=True)
class Route:
    resources:frozenset
    actions:tuple
    quantities:tuple
    value:float
    @property
    def utility(self):return self.value-8*len(self.actions)

@dataclass(frozen=True)
class Task:
    resource:tuple
    target:tuple
    commands:tuple
    item:str
    units:int

def r(resource='A',value=100,command='NORTH',quantity=1,work=1):
    return Route(frozenset([resource]) if resource else frozenset(),((command,),)*work,(quantity,),value)
def pas():return Route(frozenset(),(),(0,),0.)

def brute_assign(menu,room,obs=None):
    """Independent itertools oracle, with an artificial constant-price objective."""
    best=None;chosen=None;leaves=0
    for candidate in product(*menu):
        used=set();ok=True
        for route in candidate:
            if used & route.resources:ok=False;break
            used.update(route.resources)
        if not ok:continue
        qty=sum(sum(x.quantities) for x in candidate)
        if qty>room:continue
        leaves+=1;work=sum(len(x.actions) for x in candidate)
        value=sum(x.value for x in candidate)
        key=(value-8*work,-work)
        if best is None or key>best:best=key;chosen=list(candidate)
    if best is None:raise ValueError('No feasible assignment')
    return chosen,{'joint_utility':best[0],'joint_work':-best[1],
                   'joint_units':sum(sum(r.quantities) for r in chosen),'assignment_leaves':leaves}

def routing_fixture(tasks=()):
    def walk(p,t):
        commands=[];p=list(p)
        while tuple(p)!=tuple(t):
            if p[0]<t[0]:p[0]+=1;cmd='EAST'
            elif p[0]>t[0]:p[0]-=1;cmd='WEST'
            elif p[1]<t[1]:p[1]+=1;cmd='SOUTH'
            else:p[1]-=1;cmd='NORTH'
            commands.append((cmd,))
        return commands,tuple(p)
    return SimpleNamespace(Route=Route,ITEMS=('WHEAT',),SHED=((4,4),(4,5),(5,4),(5,5)),
        distance=lambda p,q:abs(p[0]-q[0])+abs(p[1]-q[1]),walk=walk,
        collections=lambda obs:list(tasks),sale_revenue=lambda i,inv,q:25*q,
        game=SimpleNamespace(_farmer_position=lambda farm,i:farm['farmer'] if i==0 else farm['hands'][i-1]))

def observation(step=696,hands=0,carried=0):
    farm={'money':100.,'farmer':[4,4],'hands':[[4,4] for _ in range(hands)],'tiles':[[None]*10 for _ in range(10)]}
    return {'step':step,'day':step//24,'hour':step%24,'player':0,'farms':[deepcopy(farm),deepcopy(farm)],
            'private':{'shed':{'WHEAT':0},'inventories':[{'WHEAT':carried} for _ in range(hands+1)],'seeds':{}},
            'market':{'inventory':{'WHEAT':10000},'prices':{'WHEAT':25}},'town':{'unlocked_shops':[]}}
