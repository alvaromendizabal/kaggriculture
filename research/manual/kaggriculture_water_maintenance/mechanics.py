"""Mandatory comparison to installed official crop primitives, not a mock engine."""
from copy import deepcopy
from itertools import product
from water_features import next_refresh, features

def verify_mechanics(game):
    rows = []
    for crop, p in game.CROPS.items():
        ages = sorted({0, max(0, p['first_yield_day'] - 1), p['first_yield_day'], p['max_yield_day'], p['max_yield_day'] + 1})
        for age, dry, fertile, watered, units, hour in product(ages, (0, 1), (False, True), (False, True), (0, p['max_yield']), (0, 23)):
            day = max(15, age + 1)
            tile = game._new_plant(crop, day - age, 24)
            tile.update(consecutive_unwatered=dry, watered_today=watered, yield_units=units, fertilized_until_day=day if fertile else -1)
            obs = {'day': day, 'hour': hour, 'step': day * 24 + hour, 'market': {'prices': {crop: game.market_price(crop, 10000)}}}
            for do_water in (False, True):
                predicted = next_refresh(tile, day, hour, game.CROPS, do_water)
                farm = game._new_farm(10, 3000)
                private = game._new_private()
                farm['tiles'][4][4] = deepcopy(tile)
                if do_water:
                    game._apply_unit_action(farm, private, 0, ['WATER'], 10, day, 24, 100)
                for step in range(day * 24 + hour, day * 24 + 24):
                    game._decay_plants(farm, step)
                game._daily_refresh_plants(farm, day, 24)
                if farm['tiles'][4][4] != predicted:
                    raise ValueError('Official WATER/decay/refresh parity failed: ' + repr((crop, age, dry, fertile, watered, units, hour, do_water, predicted, farm['tiles'][4][4])))
            f = features(tile, obs, game.CROPS)
            if f['defer_eligible'] and (f['survival_gain'] or f['water_bonus_now'] or f['next_units_delta'] > 0):
                raise ValueError('Deferral admitted an immediate/next-refresh benefit')
            rows.append({'crop': crop, 'age': age, 'hour': hour, 'dry': dry, 'fertile': fertile, 'already_watered': watered, 'units': units, 'official_branches_checked': 2, 'passed': True})
    return rows
