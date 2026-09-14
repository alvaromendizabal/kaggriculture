"""Artificial states and toy prices for unit tests, NOT competition measurements."""
from opportunity_features import Rules

def price(item, inventory):
    base={'WHEAT':25,'CARROT':35,'EGG':50,'MILK':160,'FERTILIZER':100}[item]
    return max(1,base-max(0,inventory-10000)//2)

RULES=Rules({'WHEAT':{'first_yield_day':2},'CARROT':{'first_yield_day':2}},
            {'GOOSE':{'product':'EGG'},'COW':{'product':'MILK'}},
            ('WHEAT','CARROT','EGG','MILK','FERTILIZER'),price)

def fixture(hands=2, seat=0, hour=12):
    farms=[]
    for _ in (0,1):
        tiles=[[None for _ in range(10)] for _ in range(10)]
        for x,y,crop,n in ((4,4,'WHEAT',3),(1,1,'CARROT',4)):
            tiles[y][x]={'kind':'PLANT','crop':crop,'planted_day':26,'yield_units':n,
                          'max_lifespan_step':720,'watered_today':True,'consecutive_unwatered':0}
        tiles[4][6]={'kind':'COOP','animal':'GOOSE','yield_units':4}
        farms.append({'tiles':tiles,'money':1000,'farmer':[4,4],
                      'hands':[[i%10,(i//10)%10] for i in range(hands)],
                      'unlocked_quadrants':['NW'],'hires_today':hands})
    return {'player':seat,'day':29,'hour':hour,'step':696+hour,'farms':farms,
            'private':{'shed':{'WHEAT':5},'seeds':{},'inventories':[{} for _ in range(hands+1)]},
            'market':{'inventory':{p:10000 for p in RULES.products},
                      'prices':{p:price(p,10000) for p in RULES.products}},'town':{'unlocked_shops':[]}}
