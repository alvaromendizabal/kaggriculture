"""Current-observation crop maintenance scenarios; no outcome or rival-private inputs.

The next-refresh projection assumes no intervening harvest, fertilizer application,
watering, digging, or replanting other than the stated WATER-now intervention.
It includes all remaining in-day decay phases. It is not a policy rollout.
"""
from __future__ import annotations
from copy import deepcopy
from math import isfinite
from numbers import Integral, Real
END = 718
FIELDS = ('age_days', 'ongoing', 'watered_today', 'dry_streak', 'hours_until_refresh', 'refresh_available', 'current_units', 'harvestable_units', 'fertilized_today', 'water_bonus_now', 'production_due_next_refresh', 'no_water_alive', 'water_alive', 'no_water_next_units', 'water_next_units', 'next_units_delta', 'survival_gain', 'no_water_next_dry_streak', 'water_next_dry_streak', 'next_day_maintenance_debt', 'defer_eligible', 'keep_water', 'remaining_production_events', 'next_production_available', 'next_production_days', 'current_quote', 'next_units_delta_quote_value', 'decay_ticks_until_refresh', 'current_holding_cap', 'next_production_headroom')
SUMMARY_FIELDS = ('plant_count', 'unwatered_plants', 'defer_eligible_plants', 'survival_critical_plants', 'immediate_bonus_plants', 'production_bonus_plants', 'deferred_next_day_tasks', 'workers', 'worker_actions_until_refresh', 'unwatered_tasks_per_worker', 'deferred_tasks_per_worker')

def integer(value, name, lower=0):
    if isinstance(value, bool) or not isinstance(value, Integral) or value < lower:
        raise ValueError(name + ': expected integer >= ' + str(lower))
    return int(value)

def clock(obs):
    day = integer(obs['day'], 'day')
    hour = integer(obs['hour'], 'hour')
    step = 24 * day + hour
    if hour >= 24 or step > END:
        raise ValueError('Outside default callback clock')
    given = obs.get('step')
    if given is not None and integer(given, 'step') != step:
        raise ValueError('Clock conflict')
    return step

def validate_tile(tile, day, crops):
    if not isinstance(tile, dict) or tile.get('kind') != 'PLANT' or tile.get('crop') not in crops:
        raise ValueError('Expected known PLANT')
    if integer(tile['planted_day'], 'planted_day') > day:
        raise ValueError('Future planting day')
    for field in ('yield_units', 'consecutive_unwatered'):
        integer(tile[field], field)
    if type(tile['watered_today']) is not bool:
        raise ValueError('watered_today must be boolean')
    integer(tile['fertilized_until_day'], 'fertilized_until_day', -1)
    integer(tile['max_lifespan_step'], 'max_lifespan_step', -1)

def water_now(tile, day, p):
    out = deepcopy(tile)
    if not out['watered_today']:
        out['watered_today'] = True
        age = day - out['planted_day']
        if not p['ongoing'] and (p['max_yield_day'] + 1) // 2 <= age <= p['max_yield_day']:
            out['yield_units'] = min(p['max_yield'], out['yield_units'] + (2 if out['fertilized_until_day'] >= day else 1))
    return out

def decay_ticks(tile, step, last):
    life = tile['max_lifespan_step']
    if life < 0 or last < life:
        return 0
    first = max(life, step)
    first += (first - life) % 2
    return 0 if first > last else (last - first) // 2 + 1

def next_refresh(tile, day, hour, crops, water=False):
    """Closed-form WATER -> remaining hourly decay -> nightly crop refresh."""
    validate_tile(tile, day, crops)
    if not 0 <= hour < 24 or not 0 <= day <= 28:
        raise ValueError('No registered next refresh')
    p = crops[tile['crop']]
    out = water_now(tile, day, p) if water else deepcopy(tile)
    n = decay_ticks(out, day * 24 + hour, day * 24 + 23)
    if n:
        out['yield_units'] -= n
        if out['yield_units'] <= 0:
            return {'kind': 'WEED'}
    watered = out['watered_today']
    out['consecutive_unwatered'] = 0 if watered else out['consecutive_unwatered'] + 1
    out['watered_today'] = False
    if out['consecutive_unwatered'] >= 2:
        return {'kind': 'WEED'}
    offset = day + 1 - out['planted_day'] - p['first_yield_day']
    if p['ongoing'] and offset >= 0 and (offset % p['interval'] == 0):
        count = offset // p['interval'] + 1
        if count <= p['max_yield']:
            fertile = watered and out['fertilized_until_day'] >= day
            out['yield_units'] = min(p['max_yield'], out['yield_units'] + (2 if fertile else 1))
            if count == p['max_yield']:
                out['max_lifespan_step'] = (day + 2) * 24
    return out

def features(tile, obs, crops):
    step = clock(obs)
    day = obs['day']
    hour = obs['hour']
    validate_tile(tile, day, crops)
    p = crops[tile['crop']]
    age = day - tile['planted_day']
    available = day < 29
    now = water_now(tile, day, p)
    bonus = now['yield_units'] - tile['yield_units']
    left = next_refresh(tile, day, hour, crops, False) if available else {'kind': 'UNAVAILABLE'}
    right = next_refresh(tile, day, hour, crops, True) if available else {'kind': 'UNAVAILABLE'}
    alive = lambda t: int(t.get('kind') == 'PLANT')
    a, b = (alive(left), alive(right))
    lu = left.get('yield_units', 0)
    ru = right.get('yield_units', 0)
    keep = not tile['watered_today'] and (not available or tile['consecutive_unwatered'] >= 1 or bonus > 0 or (b > a) or (ru > lu))
    defer = available and (not tile['watered_today']) and (not keep)
    events = []
    if p['ongoing']:
        events = [tile['planted_day'] + p['first_yield_day'] + i * p['interval'] for i in range(p['max_yield'])]
        events = [d for d in events if day < d <= 29]
    else:
        d = tile['planted_day'] + p['first_yield_day']
        events = [d] if day < d <= 29 else []
    offset = day + 1 - tile['planted_day'] - p['first_yield_day']
    due = bool(p['ongoing'] and offset >= 0 and (offset % p['interval'] == 0) and (offset // p['interval'] < p['max_yield']))
    quote = obs['market']['prices'][tile['crop']]
    if isinstance(quote, bool) or not isinstance(quote, Real) or (not isfinite(quote)) or (quote < 1):
        raise ValueError('Invalid public quote')
    values = dict(zip(FIELDS, (age, p['ongoing'], tile['watered_today'], tile['consecutive_unwatered'], 24 - hour, available, tile['yield_units'], tile['yield_units'] if age >= p['first_yield_day'] else 0, tile['fertilized_until_day'] >= day, bonus, due and available, a, b, lu, ru, ru - lu, b - a, left.get('consecutive_unwatered', 0), right.get('consecutive_unwatered', 0), bool(defer and a and (left.get('consecutive_unwatered', 0) >= 1)), defer, keep, len(events), bool(events), min(events) - day if events else 0, quote, (ru - lu) * quote, decay_ticks(tile, step, day * 24 + 23) if available else 0, p['max_yield'], max(0, p['max_yield'] - tile['yield_units'])), strict=True))
    result = {k: float(v) for k, v in values.items()}
    if not all((isfinite(v) for v in result.values())):
        raise ValueError('Nonfinite feature')
    return result

def extract(obs, game):
    """Per-plant candidates and fixed-schema aggregates; own public farm only."""
    clock(obs)
    player = integer(obs['player'], 'player')
    if player not in (0, 1) or len(obs['farms']) != 2:
        raise ValueError('Two-player observation required')
    farm = obs['farms'][player]
    if len(farm['tiles']) != 10 or any((len(r) != 10 for r in farm['tiles'])):
        raise ValueError('Expected 10x10')
    if game._resolve_market_params(obs['market'].get('params')) != game.MARKET_PARAMS:
        raise ValueError('Nondefault market configuration')
    rows = []
    for y, line in enumerate(farm['tiles']):
        for x, tile in enumerate(line):
            if isinstance(tile, dict) and tile.get('kind') == 'PLANT':
                if obs['market']['prices'][tile['crop']] != game.market_price(tile['crop'], obs['market']['inventory'][tile['crop']]):
                    raise ValueError('Quote/curve mismatch')
                rows.append({'x': x, 'y': y, 'crop': tile['crop'], **features(tile, obs, game.CROPS)})
    workers = 1 + len(farm['hands'])
    unwater = sum((1 - r['watered_today'] for r in rows))
    deferred = sum((r['defer_eligible'] for r in rows))
    values = (len(rows), unwater, deferred, sum((not r['watered_today'] and r['dry_streak'] >= 1 for r in rows)), sum((r['water_bonus_now'] > 0 for r in rows)), sum((r['next_units_delta'] > 0 and (not r['survival_gain']) for r in rows)), sum((r['next_day_maintenance_debt'] for r in rows)), workers, workers * (24 - obs['hour']), unwater / workers, deferred / workers)
    return (rows, dict(zip(SUMMARY_FIELDS, map(float, values), strict=True)))
