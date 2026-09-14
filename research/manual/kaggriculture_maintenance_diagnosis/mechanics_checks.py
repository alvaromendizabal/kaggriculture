"""Compare interaction scenarios to real installed engine components before replay."""
from copy import deepcopy
from interaction_features import conditional_path
from crop_dynamics import next_refresh

def plant_fixture(game,crop,day,age,units,watered,fertile):
    t=game._new_plant(crop,max(0,day-age),24)
    t.update(yield_units=units,watered_today=watered,consecutive_unwatered=0,
             fertilized_until_day=day if fertile else -1)
    return t

def oracle_path(game,tile,day,hour,water,harvest):
    farm=game._new_farm(10,3000); farm['farmer']=[1,1]; farm['tiles'][1][1]=deepcopy(tile)
    private=game._new_private(); original=tile['crop']
    for step in range(day*24+hour,day*24+24):
        action=['WATER'] if water and step==day*24+hour else ['HARVEST'] if harvest and step==day*24+hour+1 else ['PASS']
        game._apply_unit_action(farm,private,0,action,10,day,24,100)
        game._decay_plants(farm,step)
    game._daily_refresh_plants(farm,day,24)
    t=farm['tiles'][1][1]; collected=private['inventories'][0].get(original,0)
    return {'tile':t,'harvested':collected,'total_units':collected+(t.get('yield_units',0) if isinstance(t,dict) else 0)}

def validate(game):
    cases=[]
    for crop,p in game.CROPS.items():
        for day,age in [(20,p['first_yield_day']),(20,p['max_yield_day']+1),(27,p['first_yield_day'])]:
            for units in (1,p['max_yield']):
                for hour in (0,22):
                    for fertile in (False,True):
                        t=plant_fixture(game,crop,day,age,units,False,fertile)
                        obs={'day':day,'hour':hour,'step':day*24+hour}
                        for water,harvest in [(False,False),(True,False),(False,True),(True,True)]:
                            left=conditional_path(t,obs,game.CROPS,water,harvest)
                            right=oracle_path(game,t,day,hour,water,harvest)
                            if left!=right: raise ValueError(f'Interaction parity: {crop}, day={day}, age={age}, hour={hour}, water={water}, harvest={harvest}')
                            cases.append({'crop':crop,'day':day,'age':age,'hour':hour,'units':units,'fertile':fertile,'water':water,'harvest':harvest,'total_units':left['total_units']})
    return {'status':'PASSED','component_scenarios':len(cases),'cases':cases,
      'scope':'Copied artificial states; exact component parity, not live policy benefit'}
