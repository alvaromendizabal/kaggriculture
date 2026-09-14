"""Terminal worker/action candidates from current legal observations only.

Values are explicitly frozen-market, no-intervening-trade scenarios. They are
not future cash predictions, optimal joint schedules, or a competition agent.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
import math
from typing import Any, Callable, Mapping

from workforce_features import canonical_observation, integer, position, distance, SHED_ACCESS

SCHEMA = 'terminal-action-opportunity-v1'
ARMS = ('full', 'no_deadline', 'no_decay', 'no_capacity', 'no_price_impact')
MOVES = (('NORTH', 0, -1), ('WEST', -1, 0), ('SOUTH', 0, 1), ('EAST', 1, 0))

@dataclass(frozen=True)
class Rules:
    crops: Mapping[str, Mapping[str, Any]]
    animals: Mapping[str, Mapping[str, Any]]
    products: tuple[str, ...]
    price: Callable[[str, int], float]
    market_params: Mapping[str, Mapping[str, Any]] | None = None

    @classmethod
    def from_game(cls, game):
        return cls(game.CROPS, game.ANIMALS, tuple(game.PRODUCTS), game.market_price, game.MARKET_PARAMS)


def route(start, finish):
    """Deterministic Manhattan path; locked tiles do not block movement in this pin."""
    x, y = position(start); tx, ty = position(finish)
    result = []
    while (x, y) != (tx, ty):
        for op, dx, dy in MOVES:
            nx, ny = x+dx, y+dy
            if 0 <= nx < 10 and 0 <= ny < 10 and distance((nx,ny),(tx,ty)) < distance((x,y),(tx,ty)):
                result.append(op); x,y=nx,ny; break
        else:
            raise ValueError('No decreasing Manhattan step')
    return result


def nearest_shed(p):
    return min(SHED_ACCESS, key=lambda q: (distance(p,q), SHED_ACCESS.index(q)))


def decay_units(tile, step: int, travel: int):
    """Yield just before HARVEST at step+travel; only intervening turn decay.

    This is restricted to the final day: no refresh or production is crossed
    by any candidate admitted by the deadline gate.
    """
    n = integer(tile['yield_units'], 'yield_units')
    travel = integer(travel, 'travel')
    if tile.get('kind') != 'PLANT': return n
    m = tile.get('max_lifespan_step')
    if type(m) is not int or m < -1: raise ValueError('Missing/invalid max_lifespan_step')
    if m < 0 or travel == 0: return n
    low, high = max(step,m), step+travel-1
    first = low + ((m-low) % 2)
    events = 0 if first > high else (high-first)//2+1
    return max(0, n-events)


def admitted_drop(inventory, room):
    """Official DROP dictionary order; overflow disappears even for unsellable items."""
    room=integer(room,'room'); accepted={}
    for item, quantity in inventory.items():
        n=integer(quantity, 'inventory.'+item)
        take=min(n,room)
        if take: accepted[item]=take
        room -= take
    return accepted


def sale_prefix(price, item, inventory, quantity):
    """One-sided same-callback sale curve; floor-price sales do not add supply."""
    quantity=integer(quantity,'quantity')
    total=0.0
    for _ in range(quantity):
        p=float(price(item,inventory))
        if not math.isfinite(p) or p < 1: raise ValueError('Invalid market price')
        total+=p
        inventory+=int(p>1)
    return total,inventory


def incremental_value(accepted, shed, market, rules, linear=False):
    total=0.0
    for item,n in accepted.items():
        if item not in rules.products: continue
        if linear:
            total+=n*rules.price(item,market[item])
        else:
            _,post=sale_prefix(rules.price,item,market[item],shed.get(item,0))
            total+=sale_prefix(rules.price,item,post,n)[0]
    return float(total)


def ready_resources(farm, day, rules):
    tasks=[]
    for y,row in enumerate(farm['tiles']):
        for x,t in enumerate(row):
            if not isinstance(t,Mapping): continue
            if t.get('kind')=='PLANT':
                crop=t['crop']
                if crop not in rules.crops: raise ValueError('Unknown crop')
                age=day-integer(t['planted_day'],'planted_day')
                if age<0: raise ValueError('Plant comes from the future')
                if age < rules.crops[crop]['first_yield_day']: continue
                item=crop
            elif t.get('animal'):
                if t['animal'] not in rules.animals: raise ValueError('Unknown animal')
                item=rules.animals[t['animal']]['product']
            else: continue
            units=integer(t.get('yield_units',0),'yield_units')
            if units:
                tasks.append({'task_id':f'harvest:{x}:{y}','x':x,'y':y,'item':item,'units':units,'tile':t})
    return tasks


@dataclass
class Result:
    state: dict[str,float]
    candidates: list[dict[str,Any]]
    choices: list[dict[str,Any]]


def extract_opportunities(observation, rules: Rules) -> Result:
    obs=canonical_observation(observation)
    if obs['day'] != 29: raise ValueError('This registered round supports final-day observations only')
    market_raw=observation['market']
    overrides=market_raw.get('params')
    if overrides:
        if rules.market_params is None: raise ValueError('Unregistered market parameter overrides')
        resolved={k:dict(v) for k,v in rules.market_params.items()}
        for item,patch in overrides.items():
            if item not in resolved or not isinstance(patch,Mapping): raise ValueError('Invalid market overrides')
            resolved[item].update(patch)
        if resolved!=rules.market_params: raise ValueError('Only pinned default market curves are supported')
    market={item:integer(market_raw['inventory'][item], 'market inventory') for item in rules.products}
    for item in rules.products:
        quoted=market_raw['prices'][item]
        if not math.isfinite(quoted) or quoted!=rules.price(item,market[item]):
            raise ValueError('Observation price differs from pinned default curve')
    farm=obs['farms'][obs['player']]; private=obs['private']
    positions=[farm['farmer'],*farm['hands']]
    steps_left=719-obs['step']; shed=private['shed']
    shed_used=sum(shed.values())
    if shed_used>100: raise ValueError('Observed shed exceeds pinned capacity')
    room=100-shed_used
    tasks=ready_resources(farm,29,rules)
    candidates=[]
    for worker_index,p in enumerate(positions):
        carried=private['inventories'][worker_index]
        # Include one real delivery alternative for held inventory, then every ready task.
        options=([None] if sum(carried.values()) else [])+tasks
        for task in options:
            if task is None:
                target=p; travel=0; harvested=0; visible=0; item=''; task_id='deliver'
                actions=route(p,nearest_shed(p))+['DROP']
                approach=[]
            else:
                target=(task['x'],task['y']);approach=route(p,target);travel=len(approach)
                visible=task['units']; harvested=decay_units(task['tile'],obs['step'],travel)
                item=task['item'];task_id=task['task_id']
                actions=approach+['HARVEST']+route(target,nearest_shed(target))+['DROP']
            inv=dict(carried); undecayed=dict(carried)
            if task is not None:
                if harvested: inv[item]=inv.get(item,0)+harvested
                undecayed[item]=undecayed.get(item,0)+visible
            accepted=admitted_drop(inv,room)
            old_accepted=admitted_drop(carried,room)
            undecayed_accepted=admitted_drop(undecayed,room)
            revenue=incremental_value(accepted,shed,market,rules)
            base_revenue=incremental_value(old_accepted,shed,market,rules)
            no_decay_revenue=incremental_value(undecayed_accepted,shed,market,rules)
            no_capacity_revenue=incremental_value(inv,shed,market,rules)
            linear_revenue=incremental_value(accepted,shed,market,rules,linear=True)
            cost=len(actions); alive=task is None or harvested>0
            feasible=bool(cost<=steps_left and alive)
            # All rates are transparent candidate-ranking probes, not learned utility.
            rates={'full':revenue/cost if feasible else 0.0,
                   'no_deadline':revenue/cost if alive else 0.0,
                   'no_decay':no_decay_revenue/cost if cost<=steps_left else 0.0,
                   'no_capacity':no_capacity_revenue/cost if feasible else 0.0,
                   'no_price_impact':linear_revenue/cost if feasible else 0.0}
            worker_costs=([len(route(q,target))+1+distance(target,nearest_shed(target))+1 for q in positions]
                          if task else [])
            eligible=(sum(c<=steps_left and decay_units(task['tile'],obs['step'],distance(q,target))>0
                          for c,q in zip(worker_costs,positions)) if task else 0)
            alternatives=sorted(c for i,c in enumerate(worker_costs) if i!=worker_index)
            candidate={'worker_index':worker_index,'is_farmer':int(worker_index==0),
                'candidate_id':f'w{worker_index}:{task_id}','task_id':task_id,
                'kind':'harvest_then_drop' if task else 'drop_carried',
                'product':item,'target_x':target[0],'target_y':target[1],
                'first_action':actions[0], 'plan':actions,
                'travel_actions':travel,'manual_cash_actions':cost,
                'decisions_remaining':steps_left,'deadline_slack':steps_left-cost,
                'within_deadline':int(cost<=steps_left),'yield_alive_on_arrival':int(alive),
                'visible_harvest_units':visible,'arrival_harvest_units':harvested,
                'decayed_units_en_route':visible-harvested,
                'carried_units':sum(carried.values()),'shed_room_now':room,
                'accepted_units':sum(accepted.values()),'discarded_units':sum(inv.values())-sum(accepted.values()),
                'frozen_bundle_revenue':revenue,'marginal_harvest_revenue':revenue-base_revenue if task else 0.0,
                'price_impact_loss':linear_revenue-revenue,
                'capacity_value_loss':no_capacity_revenue-revenue,
                'no_decay_revenue':no_decay_revenue,
                'independent_eligible_workers':eligible,
                'only_eligible_worker':int(task is not None and eligible==1 and feasible),
                'other_worker_present':int(bool(alternatives)),
                'fastest_other_worker_actions':alternatives[0] if alternatives else 0,
                'travel_advantage_vs_other':alternatives[0]-cost if alternatives else 0,
                **{arm+'_rate':float(value) for arm,value in rates.items()}}
            candidates.append(candidate)
        candidates.append({'worker_index':worker_index,'is_farmer':int(worker_index==0),
            'candidate_id':f'w{worker_index}:pass','task_id':'pass','kind':'pass','product':'',
            'target_x':p[0],'target_y':p[1],'first_action':'PASS','plan':['PASS'],
            **{k:0 for k in candidate_numeric_fields()},
            **{arm+'_rate':0.0 for arm in ARMS}})
    # Action-level opportunity costs exclude alternatives with the SAME first command.
    choices=[]
    for worker in range(len(positions)):
        group=[r for r in candidates if r['worker_index']==worker]
        for r in group:
            other=[a['full_rate'] for a in group if a['first_action']!=r['first_action']]
            r['other_first_action_present']=int(bool(other))
            r['best_other_first_action_rate']=max(other,default=0.0)
            r['first_action_regret_rate']=max(a['full_rate'] for a in group)-max(a['full_rate'] for a in group if a['first_action']==r['first_action'])
        baseline=None
        for arm in ARMS:
            selected=choose(group,arm)
            if arm=='full': baseline=selected
            choices.append({'worker_index':worker,'arm':arm,'candidate_id':selected['candidate_id'],
                'task_id':selected['task_id'],'first_action':selected['first_action'],
                'selected_rate':selected[arm+'_rate'],
                'changed_first_action':int(selected['first_action']!=baseline['first_action']),
                'changed_task':int(selected['task_id']!=baseline['task_id'])})
    picks=[r for r in choices if r['arm']=='full']
    target_counts=defaultdict(int)
    for row in picks:
        if row['task_id'] not in ('pass','deliver'): target_counts[row['task_id']]+=1
    for row in candidates:
        row['independent_top_task_claimants']=target_counts[row['task_id']] if row['task_id'] not in ('pass','deliver') else 0
    nonpass=[r for r in candidates if r['kind']!='pass']
    state={'action.worker_count':float(len(positions)),'action.visible_resources':float(len(tasks)),
        'action.candidates':float(len(nonpass)), 'action.deadline_feasible_candidates':float(sum(r['within_deadline'] for r in nonpass)),
        'action.arrival_decay_candidates':float(sum(r['decayed_units_en_route']>0 for r in nonpass)),
        'action.positive_opportunity_candidates':float(sum(r['full_rate']>0 for r in nonpass)),
        'action.capacity_loss_candidates':float(sum(r['capacity_value_loss']>0 for r in nonpass)),
        'action.price_impact_candidates':float(sum(r['price_impact_loss']>0 for r in nonpass)),
        'action.negative_marginal_harvest_candidates':float(sum(r['marginal_harvest_revenue']<0 for r in nonpass)),
        'action.contested_top_tasks':float(sum(n>1 for n in target_counts.values())),
        'action.workers_claiming_contested_top_tasks':float(sum(n for n in target_counts.values() if n>1)),
        'action.pass_selections':float(sum(r['first_action']=='PASS' for r in picks)),
        'action.maximum_individual_rate':float(max((r['selected_rate'] for r in picks),default=0)),
        'action.mean_individual_rate':float(sum(r['selected_rate'] for r in picks)/len(positions))}
    for arm in ARMS[1:]:
        state['probe.'+arm+'.changed_first_actions']=float(sum(r['changed_first_action'] for r in choices if r['arm']==arm))
        state['probe.'+arm+'.changed_tasks']=float(sum(r['changed_task'] for r in choices if r['arm']==arm))
    # No sum of independent worker revenues is reported as realizable joint value.
    for value in state.values():
        if not math.isfinite(value): raise ValueError('Non-finite state feature')
    for r in candidates:
        for k,v in r.items():
            if isinstance(v,(int,float)) and not math.isfinite(v): raise ValueError('Non-finite candidate '+k)
    return Result(state,candidates,choices)


def candidate_numeric_fields():
    return ('travel_actions','manual_cash_actions','decisions_remaining','deadline_slack',
        'within_deadline','yield_alive_on_arrival','visible_harvest_units','arrival_harvest_units',
        'decayed_units_en_route','carried_units','shed_room_now','accepted_units','discarded_units',
        'frozen_bundle_revenue','marginal_harvest_revenue','price_impact_loss','capacity_value_loss',
        'no_decay_revenue','independent_eligible_workers','only_eligible_worker','other_worker_present',
        'fastest_other_worker_actions','travel_advantage_vs_other')


def choose(rows,arm):
    if arm not in ARMS: raise ValueError('Unknown probe arm')
    # PASS wins all zero-value ties; do not assign unproductive work just to get divergence.
    return min(rows,key=lambda r:(-r[arm+'_rate'],int(r['kind']!='pass'),r['manual_cash_actions'],r['task_id']))
