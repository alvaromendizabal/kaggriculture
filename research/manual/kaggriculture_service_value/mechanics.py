"""User-run installed-engine fixtures; never counted as competition games."""
from copy import deepcopy
from itertools import product
from feature_common import distance,shed_distance

def walk(a,b):
    a=list(a);commands=[]
    while a[0]!=b[0]:
        op='EAST' if a[0]<b[0] else 'WEST';a[0]+=1 if op=='EAST' else -1;commands.append([op])
    while a[1]!=b[1]:
        op='SOUTH' if a[1]<b[1] else 'NORTH';a[1]+=1 if op=='SOUTH' else -1;commands.append([op])
    return commands

def validate(game,rid,make_environment=None):
    n=0;transitions=0
    if rid=='19':
        from collection_features import timing
        for start,target,op in product(((0,0),(4,4),(9,9)),((0,4),(4,4),(9,9)),('HARVEST','COLLECT_FERTILIZER')):
            farm=game._new_farm(10,3000);private=game._new_private();farm['farmer']=list(start)
            tile=game._new_plant('WHEAT',7,24) if op=='HARVEST' else game._new_animal('GOOSE',6)
            tile['yield_units']=3;tile['fertilizer_available']=True
            x,y=target;farm['tiles'][y][x]=tile
            shed=min(((4,4),(4,5),(5,4),(5,5)),key=lambda p:(distance(target,p),p))
            actions=walk(start,target)+[[op]]+walk(target,shed)+[['DROP']]
            item='WHEAT' if op=='HARVEST' else 'FERTILIZER';quantity=3 if op=='HARVEST' else 1
            for i,a in enumerate(actions):
                game._apply_unit_action(farm,private,0,a,10,10,24,100)
                if i<len(actions)-1 and private['shed'].get(item,0):raise ValueError('Deposit timing fixture failed')
            if private['shed'].get(item)!=quantity or private['inventories'][0].get(item,0):raise ValueError('Collected quantity/deposit mismatch')
            predicted_manual_offset=timing(240,distance(start,target),shed_distance(target))[2]
            if len(actions)-1!=predicted_manual_offset:raise ValueError('Manual sale offset mismatch')
            n+=1
        if make_environment is None:raise ValueError('Live nightly-order fixture requires official environment')
        for seat in (0,1):
            env=make_environment(0)
            for _ in range(23):env.step([{'farmer':['PASS'],'hands':[],'market':[]} for _ in (0,1)]);transitions+=1
            farm=env.state[0].observation.farms[seat];farm['farmer']=[0,0]
            private=env.state[seat].observation.private;private['inventories'][0]['WHEAT']=3
            before=farm['money'];orders=[{'farmer':['PASS'],'hands':[],'market':[]} for _ in (0,1)]
            orders[seat]['market']=[['SELL','WHEAT',3]];env.step(orders);transitions+=1
            farm=env.state[0].observation.farms[seat];private=env.state[seat].observation.private
            if farm['money']!=before or private['shed']['WHEAT']!=3:raise ValueError('Night deposit must follow current market phase')
            inv=env.state[0].observation.market['inventory']['WHEAT'];expected=0
            for _ in range(3):
                p=game.market_price('WHEAT',inv);expected+=p;inv+=int(p>1)
            env.step(orders);transitions+=1
            if env.state[0].observation.farms[seat]['money']-before!=expected:raise ValueError('Next-callback nightly liquidation mismatch')
            n+=1
        scope='Manual movement/collection/deposit primitives and both-seat overnight sale ordering'
    elif rid=='20':
        # Mortality effects are checked independently of the new priority formula.
        for species,streak,done,resource,apply in product(['WHEAT','TOMATO','GOOSE','COW','SHEEP'],(0,1),(False,True),(0,1),(False,True)):
            farm=game._new_farm(10,3000);private=game._new_private();farm['farmer']=[4,4]
            animal=species in game.ANIMALS
            t=game._new_animal(species,0) if animal else game._new_plant(species,0,24)
            t['yield_units']=1
            flag='fed_today' if animal else 'watered_today';counter='consecutive_unfed' if animal else 'consecutive_unwatered'
            t[flag]=done;t[counter]=streak;farm['tiles'][4][4]=t;private['inventories'][0]={'WHEAT':resource}
            if apply:game._apply_unit_action(farm,private,0,['FEED' if animal else 'WATER'],10,10,24,100)
            successful=done or (apply and (not animal or resource>0))
            expected_alive=successful or streak<1
            if animal:game._daily_refresh_animals(farm,10)
            else:game._daily_refresh_plants(farm,10,24)
            after=farm['tiles'][4][4];alive=bool(after.get('animal')) if animal else after.get('kind')=='PLANT'
            if alive!=expected_alive:raise ValueError('Critical maintenance survival mismatch')
            n+=1
        scope='WATER/FEED resource use and next-refresh survival, five species'
    else:raise ValueError('Unknown round')
    return {'status':'MECHANICS_PASSED','round':rid,'cases':n,'artificial_interpreter_transitions':transitions,
            'scope':scope,'new_complete_games':0,'performance_evidence':False}
