"""Observation-only cross-worker opportunity costs for the existing route menu.

No rewards, seed, opponent private data, learned weights, or future replay rows
enter these functions. Scores are conditional route-menu descriptors, not cash
predictions. Both arms use the same candidates, eight-slot menu cap, capacity,
resource exclusions, price curves and exact assignment objective.
"""
from __future__ import annotations
from itertools import permutations
import math

MAX_GENERATED = 25000  # fail closed, never truncate a candidate pool
MENU_SIZE = 8
FIELDS = (
    'actions','units','resources','solo_value','solo_utility','original_rank',
    'in_original_menu','incumbent','direct_deposit','competing_workers',
    'preferred_resource_conflicts','opportunity_cost_sum','opportunity_cost_max',
    'compatible_alternative_mean','relative_utility','original_menu_exclusion',
)


def rank_key(route):
    return (-route.utility, len(route.actions), route.actions)


def retain_original(pool, pass_route, limit=MENU_SIZE):
    """Byte-for-byte semantic equivalent of the pinned retained-menu rule."""
    if not isinstance(limit, int) or limit < 2:
        raise ValueError('Menu limit must be an integer >= 2')
    options=sorted(pool,key=rank_key)
    retained=options[:limit]
    direct=next((r for r in options if not r.resources),None)
    if direct is not None and direct not in retained:
        retained[-1:]=[direct]
    return retained+[pass_route]


def enumerate_routes(obs, routing):
    """Expose (not expand) the pinned zero/one/two-collection candidate pool.

    Frozen helpers supply tasks, movement, prices, Route and game constants.
    The live screen checks our original retained menus against routing.menus.
    No registry or frozen file is patched.
    """
    farm=obs['farms'][obs['player']]; private=obs['private']
    if obs['day']!=29 or not 696 <= obs['step'] <= 718:
        raise ValueError('This registered study is final-day only')
    if any(len(f['hands'])>3 for f in obs['farms']):
        raise ValueError('Callback scope remains <=3 hired hands per farm; no truncation')
    if len(private['inventories'])!=1+len(farm['hands']):
        raise ValueError('Worker inventory alignment mismatch')
    tasks=routing.collections(obs)
    generated_upper=(1+len(farm['hands']))*(1+len(tasks)+len(tasks)*max(0,len(tasks)-1))
    if generated_upper>MAX_GENERATED:
        raise ValueError('Route enumeration safety bound exceeded; no partial pool accepted')
    budget=min(23,max(0,719-obs['step']))
    room=max(0,100-sum(private['shed'].values()))
    pools=[];generated=feasible=0
    for unit in range(1+len(farm['hands'])):
        position=tuple(routing.game._farmer_position(farm,unit))
        carried=private['inventories'][unit]; options=[]
        paths=[(),*((t,) for t in tasks),*permutations(tasks,2)]
        for path in paths:
            if len({t.resource for t in path})!=len(path):
                continue
            generated+=1
            quantities={item:carried.get(item,0) for item in routing.ITEMS}
            actions=[];current=position
            for task in path:
                moves,current=routing.walk(current,task.target)
                actions.extend(moves);actions.extend(task.commands)
                quantities[task.item]+=task.units
            if any(n for item,n in carried.items() if item not in routing.ITEMS):
                continue
            if not sum(quantities.values()) or sum(quantities.values())>room:
                continue
            shed=min(routing.SHED,key=lambda s:(routing.distance(current,s),s))
            moves,_=routing.walk(current,shed);actions.extend(moves);actions.append(('DROP',))
            if len(actions)>budget:
                continue
            feasible+=1
            value=sum(routing.sale_revenue(i,obs['market']['inventory'][i],q) for i,q in quantities.items())
            if not math.isfinite(value):
                raise ValueError('Nonfinite scenario value')
            options.append(routing.Route(frozenset(t.resource for t in path),tuple(actions),
                                         tuple(quantities[i] for i in routing.ITEMS),value))
        pools.append(sorted(options,key=rank_key))
    pas=routing.Route(frozenset(),(),(0,)*len(routing.ITEMS),0.0)
    menus=[retain_original(p,pas) for p in pools]
    meta={'routes_generated':generated,'routes_feasible':feasible,
          'routes_retained':sum(len(m)-1 for m in menus),
          'resources':len({t.resource for t in tasks}),'room':room,'budget':budget}
    return pools,menus,meta


def complementary_menu(pools,menus,incumbents,limit=MENU_SIZE):
    """Rescore only menu admission with a unit-coefficient opportunity-cost signal.

    For each rival *own worker*, loss is its best original-menu utility minus
    its best original-menu utility avoiding this route's resources. Sum is an
    independent-worker pressure approximation, not a feasible joint loss.
    Always keep each worker's incumbent and direct deposit, preserving a
    feasible incumbent joint assignment in the candidate menu.
    """
    if not (len(pools)==len(menus)==len(incumbents)) or not pools:
        raise ValueError('Worker/menu alignment mismatch')
    if not isinstance(limit,int) or limit<2:
        raise ValueError('Need room for incumbent and direct route')
    if any(not any(not r.actions and not r.resources and not any(r.quantities) for r in m) for m in menus):
        raise ValueError('Every menu requires a zero-valued PASS')
    independent=[max(r.utility for r in m) for m in menus]
    bests=[max(m,key=lambda r:(r.utility,-len(r.actions))) for m in menus]
    result=[];rows=[]
    for unit,pool in enumerate(pools):
        if incumbents[unit] not in menus[unit]:
            raise ValueError('Incumbent not in original menu')
        scored=[]
        for ix,r in enumerate(pool):
            losses=[];compatible=[];conflicts=0
            for other,menu in enumerate(menus):
                if other==unit:continue
                alternative=max(x.utility for x in menu if not x.resources & r.resources)
                compatible.append(alternative)
                losses.append(max(0.,independent[other]-alternative))
                conflicts+=int(bool(bests[other].resources & r.resources))
            pressure=sum(losses); adjusted=r.utility-pressure
            row={'worker':unit,'candidate':ix,'first_command':r.actions[0][0] if r.actions else 'PASS',
                 'resource_signature':';'.join(','.join(map(str,x)) for x in sorted(r.resources))}
            vals={'actions':len(r.actions),'units':sum(r.quantities),'resources':len(r.resources),
                  'solo_value':r.value,'solo_utility':r.utility,'original_rank':ix+1,
                  'in_original_menu':int(r in menus[unit]),'incumbent':int(r==incumbents[unit]),
                  'direct_deposit':int(not r.resources),'competing_workers':sum(v>0 for v in losses),
                  'preferred_resource_conflicts':conflicts,'opportunity_cost_sum':pressure,
                  'opportunity_cost_max':max(losses,default=0.),
                  'compatible_alternative_mean':sum(compatible)/max(1,len(compatible)),
                  'relative_utility':adjusted,'original_menu_exclusion':int(r not in menus[unit])}
            if set(vals)!=set(FIELDS) or not all(math.isfinite(x) for x in vals.values()):
                raise ValueError('Feature schema/value error')
            row.update({'route.'+k:float(v) for k,v in vals.items()})
            rows.append(row);scored.append((r,adjusted,ix,row))
        # Preserve incumbent order/cap. PASS is separate from the eight slots.
        keep=[]
        if incumbents[unit].actions:keep.append(incumbents[unit])
        direct=next((r for r in pool if not r.resources),None)
        if direct is not None and direct not in keep:keep.append(direct)
        for r,score,ix,row in sorted(scored,key=lambda v:(-v[1],v[2])):
            if len(keep)>=limit:break
            if r not in keep:keep.append(r)
        keep.sort(key=rank_key)
        pas=next(r for r in menus[unit] if not r.actions and not r.resources and not any(r.quantities))
        result.append(keep+[pas])
        for r,_,_,row in scored:row['admitted_to_candidate_menu']=bool(r in keep)
        if len(keep)>limit or incumbents[unit] not in result[-1]:
            raise AssertionError('Incumbent/cap invariant violated')
    return result,rows


def select_plan(obs, routing, assign, mode='opportunity'):
    if mode not in ('control','opportunity'):raise ValueError('Unregistered mode')
    pools,menus,meta=enumerate_routes(obs,routing)
    incumbent,baseline=assign(menus,int(meta['room']),obs)
    candidate,rows=complementary_menu(pools,menus,incumbent)
    selected,after=assign(candidate,int(meta['room']),obs)
    before_key=(baseline['joint_utility'],-baseline['joint_work'])
    after_key=(after['joint_utility'],-after['joint_work'])
    if after_key<before_key:
        raise AssertionError('Incumbent lost from candidate feasible set')
    improved=after_key>before_key
    # Equal-objective tie changes are not accepted as feature activation.
    chosen=selected if mode=='opportunity' and improved else incumbent
    commands=lambda routes:[list(r.actions[0]) if r.actions else ['PASS'] for r in routes]
    diag={'baseline_utility':baseline['joint_utility'],'candidate_utility':after['joint_utility'],
          'static_utility_delta':after['joint_utility']-baseline['joint_utility'],
          'baseline_work':baseline['joint_work'],'candidate_work':after['joint_work'],
          'static_key_improved':improved,'farm_commands_changed':commands(chosen)!=commands(incumbent),
          'menus_changed':sum(a!=b for a,b in zip(menus,candidate,strict=True)),
          'baseline_commands':commands(incumbent),'chosen_commands':commands(chosen),
          'routes_generated':meta['routes_generated'],'routes_feasible':meta['routes_feasible'],
          'baseline_menu_width_max':max(map(len,menus)),
          'candidate_menu_width_max':max(map(len,candidate)),
          'new_admitted_routes':sum(r not in menus[i] for i,m in enumerate(candidate) for r in m),
          'incumbent_preserved':True}
    return chosen,diag,rows,menus,meta
