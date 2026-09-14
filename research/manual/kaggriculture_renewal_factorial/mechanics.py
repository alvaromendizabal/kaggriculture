"""Exact scheduled-event checks against the installed official plant component.

Controlled plants are kept alive and emptied before each refresh to isolate
nominal production events. These are mechanics fixtures, NOT policy rollouts.
"""
from copy import deepcopy
import ast,inspect,textwrap
from lifecycle_features import schedule, exhausted_empty
from factorial_io import digest

def plant(crop,pday,crops):
    return {'kind':'PLANT','crop':crop,'planted_day':pday,'watered_today':False,
        'consecutive_unwatered':0,'yield_units':0,'fertilized_until_day':-1,
        'max_lifespan_step':-1 if crops[crop]['ongoing'] else (pday+crops[crop]['max_yield_day']+1)*24}

def core_checks(game):
    records=[]
    for crop in game.CROPS:
        for pday in (0,4,10):
            for day in range(pday,30):
                t=plant(crop,pday,game.CROPS)
                expected=[d for d in schedule(t,game.CROPS) if day<d<=29]
                farm={'tiles':[[deepcopy(t)]]};seen=[]
                for current in range(day,29):
                    cell=farm['tiles'][0][0]
                    cell['watered_today']=True;cell['yield_units']=0
                    game._daily_refresh_plants(farm,current,24)
                    if farm['tiles'][0][0]['yield_units']>0:seen.append(current+1)
                if seen!=expected:raise ValueError('Production calendar differs from engine')
                # Compare the feature with the full lifetime schedule, not just
                # events before the game ends. Future producers are never retired.
                spent=exhausted_empty(t,{'day':day,'hour':0,'step':day*24},game.CROPS)
                full=schedule(t,game.CROPS)
                if spent!=bool(full and full[-1]<=day):raise ValueError('Retirement predicate differs')
                records.append({'crop':crop,'planted_day':pday,'day':day,'expected':expected,'observed':seen,'empty_exhausted':spent})
    return records

def validate(game):
    from tests import official_refresh_excerpt as excerpt
    live=ast.dump(ast.parse(textwrap.dedent(inspect.getsource(game._daily_refresh_plants))),include_attributes=False)
    oracle=ast.dump(ast.parse(textwrap.dedent(inspect.getsource(excerpt._daily_refresh_plants))),include_attributes=False)
    if live!=oracle or game.CROPS!=excerpt.CROPS:raise ValueError('Official crop component/parameters changed')
    records=core_checks(game)
    dig_checks=0
    for crop in ('TOMATO','STRAWBERRY'):
        for pday in (0,4):
            t=plant(crop,pday,game.CROPS);day=schedule(t,game.CROPS)[-1]
            if not exhausted_empty(t,{'day':day,'hour':0},game.CROPS):raise ValueError('Invalid exhausted fixture')
            farm={'tiles':[[None for _ in range(10)] for _ in range(10)],'farmer':[4,4],'hands':[]}
            farm['tiles'][4][4]=t;private={'inventories':[{}],'shed':{},'seeds':{crop:1}}
            game._apply_unit_action(farm,private,0,['DIG'],10,day,24,100)
            if farm['tiles'][4][4] is not None:raise ValueError('DIG did not clear fixture')
            game._apply_unit_action(farm,private,0,['PLANT',crop],10,day,24,100)
            if farm['tiles'][4][4]['planted_day']!=day or private['seeds'][crop]!=0:raise ValueError('Replant mechanics differ')
            dig_checks+=1
    return {'status':'MECHANICS_PASSED','calendar_cases':len(records),'dig_replant_cases':dig_checks,
        'component_ast_sha256':digest(live),'cases':records,'full_games':0,
        'scope':'Artificial component fixtures; survival and emptying assumed for event isolation, not a yield forecast.'}
