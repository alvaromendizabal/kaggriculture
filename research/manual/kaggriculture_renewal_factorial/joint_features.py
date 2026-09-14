"""Current-state maintenance/renewal overlap features. No outcome or rival stock.

These are diagnostic candidates, not fitted scores and not extra policy changes.
Travel+3 is a one-worker DIG/PLANT/WATER optimistic work estimate, not a joint
route solution; cash, seed acquisition, other jobs, and plant survival are omitted.
"""
from __future__ import annotations
from math import isfinite
from lifecycle_features import clock, exhausted_empty, distance, ACTIVE_DAYS

DEFINITIONS = {
 'active_window': 'Day in the fixed 8..27 intervention window.',
 'current_workers': 'Farmer plus every current hired hand; no truncation.',
 'clear_eligible_spent_plots': 'Empty exhausted ongoing crop in fixed crop layout with existing replant window open.',
 'clearable_unwatered_plots': 'Eligible plot simultaneously offering an ordinary WATER job.',
 'clearable_watered_plots': 'Eligible plot already watered today; no WATER job remaining.',
 'clear_water_overlap_fraction': 'Fraction of clearable plots also unwatered; zero with no eligible plots.',
 'clearable_seed_ready_plots': 'Clearable plots with at least one matching seed presently available; not simultaneous seed feasibility.',
 'clearable_seed_missing_plots': 'Clearable plots without a matching seed in stock.',
 'water_due_plots': 'All current own plants not watered today, including spent ones.',
 'urgent_water_due_plots': 'Unwatered own plants with dry streak at least one; nominal survival need, not prediction of decay.',
 'feed_due_animals': 'Visible own animals not fed today; not an instruction to feed.',
 'urgent_feed_due_animals': 'Unfed own animals with unfed streak at least one.',
 'water_jobs_per_worker': 'Count of due WATER jobs divided by current workers; ignores travel and other jobs.',
 'clear_jobs_per_worker': 'Count of eligible clearing jobs divided by current workers.',
 'min_clear_plant_water_actions': 'Minimum over eligible plots of nearest worker Manhattan travel plus DIG, PLANT and WATER; zero if none.',
 'max_same_day_setup_slack': 'Maximum 24-hour deadline slack over those optimistic sequences; zero if none. Use eligibility count as mask.',
}
FIELDS = tuple(DEFINITIONS)


def extract(observation, game, layout):
    step = clock(observation)
    owner = observation['player']
    if type(owner) is not int or owner not in (0,1):
        raise ValueError('Invalid player')
    farm = observation['farms'][owner]
    if len(farm['tiles']) != 10 or any(len(r)!=10 for r in farm['tiles']):
        raise ValueError('Default 10x10 board required')
    workers = [farm['farmer'], *farm['hands']]
    for w in workers: distance(w, w)
    values = {f:0. for f in FIELDS}
    values.update(active_window=float(observation['day'] in ACTIVE_DAYS),current_workers=float(len(workers)))
    costs = []
    for y, row in enumerate(farm['tiles']):
        for x, tile in enumerate(row):
            if not isinstance(tile, dict): continue
            if tile.get('animal'):
                values['feed_due_animals'] += int(not tile['fed_today'])
                values['urgent_feed_due_animals'] += int(not tile['fed_today'] and tile['consecutive_unfed']>=1)
            if tile.get('kind') != 'PLANT': continue
            due = not tile['watered_today']
            values['water_due_plots'] += int(due)
            values['urgent_water_due_plots'] += int(due and tile['consecutive_unwatered']>=1)
            crop = layout.get((x,y))
            if crop and exhausted_empty(tile, observation, game.CROPS) and 719-step > game.CROPS[crop]['first_yield_day']*24+12:
                values['clear_eligible_spent_plots'] += 1
                values['clearable_unwatered_plots' if due else 'clearable_watered_plots'] += 1
                ready = observation['private']['seeds'].get(crop,0)>0
                values['clearable_seed_ready_plots' if ready else 'clearable_seed_missing_plots'] += 1
                costs.append(min(distance(w,(x,y)) for w in workers)+3)
    n=values['clear_eligible_spent_plots']
    values['clear_water_overlap_fraction']=values['clearable_unwatered_plots']/n if n else 0.
    values['water_jobs_per_worker']=values['water_due_plots']/len(workers)
    values['clear_jobs_per_worker']=n/len(workers)
    values['min_clear_plant_water_actions']=float(min(costs)) if costs else 0.
    values['max_same_day_setup_slack']=float(24-observation['hour']-min(costs)) if costs else 0.
    if not all(isfinite(v) for v in values.values()): raise ValueError('Nonfinite feature')
    return values
