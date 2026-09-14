"""Mandatory live component comparisons. Fixture outcomes never count as wins."""
from copy import deepcopy
import itertools
from feature_common import decay_tile,refresh
from headroom_features import paths

def plant(crop,day,params,units,wet,streak,fert,expiry):
    return dict(kind='PLANT',crop=crop,planted_day=day-params['first_yield_day'],watered_today=wet,
      consecutive_unwatered=streak,yield_units=units,fertilized_until_day=day if fert else -1,max_lifespan_step=expiry)
def farm(tile):
    tiles=[[None for _ in range(10)] for _ in range(10)];tiles[4][4]=deepcopy(tile)
    return {'tiles':tiles,'farmer':[4,4],'hands':[],'money':3000,'unlocked_quadrants':['NW'],'hires_today':0}
def validate(game,round_id):
    count=0;rows=[]
    # Exact in-day decay with path lengths 0..9, both expiry parities and boundaries.
    if round_id=='17':
        for crop,hour,units,travel,expiry_delta in itertools.product(game.CROPS,(0,8,18), (1,3), (0,1,4,5),(-2,0,1,4)):
            day=16;s=day*24+hour;t=plant(crop,day,game.CROPS[crop],units,True,0,False,s+expiry_delta)
            f=farm(t)
            for k in range(s,s+travel):game._decay_plants(f,k)
            expected=decay_tile(t,s,s+travel)
            if f['tiles'][4][4]!=expected:raise ValueError('Arrival-decay component parity failed')
            count+=1
        return {'status':'MECHANICS_PASSED','round':round_id,'cases':count,'new_games':0,'scope':'in-day decay projection versus installed component'}
    for crop,hour,units,wet,streak,fert,travel in itertools.product(('TOMATO','STRAWBERRY'),(0,12,20), (0,2,4),(False,True),(0,1),(False,True),(0,2)):
        day=16;s=day*24+hour;t=plant(crop,day,game.CROPS[crop],units,wet,streak,fert,-1)
        # Place strawberry on a production boundary, not only non-event days.
        if crop=='STRAWBERRY':t['planted_day']-=1
        obs={'day':day,'hour':hour,'step':s};r=paths(obs,t,travel,game)
        results=[]
        for harvest in (False,True):
            f=farm(t);private={'inventories':[{}],'shed':{},'seeds':{}}
            for k in range(s,s+24-hour):
                if harvest and k==s+travel:game._apply_unit_action(f,private,0,['HARVEST'],10,day,24,100)
                game._decay_plants(f,k)
            before=f['tiles'][4][4].get('yield_units',0)
            game._daily_refresh_plants(f,day,24)
            after=f['tiles'][4][4]
            produced=after.get('yield_units',0)-before if after.get('kind')=='PLANT' else 0
            results.append((before,int(after.get('kind')=='PLANT'),produced))
        expected=((r['before_hold'],r['hold_alive'],r['hold_produced']), (r['before_harvest'],r['harvest_alive'],r['harvest_produced']))
        if tuple(results)!=expected:raise ValueError('Production-headroom component parity failed')
        count+=1
    return {'status':'MECHANICS_PASSED','round':round_id,'cases':count,'new_games':0,'scope':'travel/harvest/decay/refresh paths versus installed components'}
