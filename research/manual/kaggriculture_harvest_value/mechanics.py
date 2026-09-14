"""Compare feature algebra against the installed engine's actual sale/demand functions."""
from copy import deepcopy
from types import SimpleNamespace
from harvest_features import marginal_value,known_demand,sale_path

def validate(game):
    sales=[];demands=[]
    for item in game.PRODUCTS:
        p=game.MARKET_PARAMS[item]
        for inv in (p['I0']-2*p['T'],p['I0'],p['I0']+p['T'],p['I0']+2*p['T'],p['I0']+1_000_000):
            for ahead in (0,7,80):
                for q in (0,4,12):
                    market={'inventory':{i:game.MARKET_PARAMS[i]['I0'] for i in game.PRODUCTS}}
                    market['inventory'][item]=inv
                    farm={'money':0.0};private={'shed':{item:ahead+q}}
                    for _ in range(ahead):
                        price=game.market_price(item,market['inventory'][item])
                        if not game._commit_unit('SELL',item,price,farm,private,market,100):raise ValueError('Failed prefix sale fixture')
                    start=farm['money']
                    for _ in range(q):
                        price=game.market_price(item,market['inventory'][item])
                        if not game._commit_unit('SELL',item,price,farm,private,market,100):raise ValueError('Failed lot sale fixture')
                    expected=marginal_value(game,item,inv,q,ahead);actual=farm['money']-start
                    if expected!=actual or private['shed'][item]!=0:raise ValueError('Marginal sale mismatch')
                    if sale_path(game,item,inv,ahead+q)[1]!=market['inventory'][item]:raise ValueError('Floor inventory mismatch')
                    sales.append({'item':item,'inventory':inv,'ahead':ahead,'q':q,'expected':expected,'actual':actual})
    shops=['PIZZA_SHOP','ICE_CREAM_SHOP','YARN_STORE','YARN_STORE']
    for step in (0,1,3,4,23,24,718):
        for delay in (0,1,4):
            inv={i:game.MARKET_PARAMS[i]['I0'] for i in game.PRODUCTS}
            market={'inventory':deepcopy(inv),'prices':{i:game.market_price(i,inv[i]) for i in inv}}
            root=SimpleNamespace(market=market,town={'unlocked_shops':shops})
            state=[SimpleNamespace(observation=root)]
            env=SimpleNamespace(configuration={'townShopSellInterval':4,'townCenterSellInterval':24})
            for t in range(step,step+delay):game._town_consume(env,state,t)
            for item in game.PRODUCTS:
                expected=known_demand(game,shops,item,step,delay);actual=inv[item]-market['inventory'][item]
                if actual!=expected:raise ValueError('Known demand phase mismatch')
                demands.append({'item':item,'step':step,'delay':delay,'expected':expected,'actual':actual})
    return {'status':'PASSED','sale_cases':len(sales),'demand_cases':len(demands),'cases':sales,'demand_checks':demands,'full_games':0}
