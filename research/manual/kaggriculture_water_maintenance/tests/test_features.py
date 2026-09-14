import unittest
from copy import deepcopy
from helpers import CROPS, plant, observation, GAME
from water_features import *

class FeatureTests(unittest.TestCase):

    def test_schema(self):
        self.assertEqual(set(features(plant(), observation(), CROPS)), set(FIELDS))

    def test_single_crop_bonus(self):
        f = features(plant(units=2), observation(), CROPS)
        self.assertEqual(f['water_bonus_now'], 1)
        self.assertEqual(f['keep_water'], 1)

    def test_fertilized_bonus(self):
        self.assertEqual(features(plant(fertile=20), observation(), CROPS)['water_bonus_now'], 2)

    def test_bonus_cap(self):
        self.assertEqual(features(plant(units=6), observation(), CROPS)['water_bonus_now'], 0)

    def test_nonbonus_defer(self):
        f = features(plant(planted=20), observation(), CROPS)
        self.assertEqual(f['defer_eligible'], 1)
        self.assertEqual(f['next_day_maintenance_debt'], 1)

    def test_death_requires_water(self):
        f = features(plant(planted=20, dry=1), observation(), CROPS)
        self.assertEqual(f['survival_gain'], 1)
        self.assertEqual(f['keep_water'], 1)

    def test_already_watered(self):
        f = features(plant(watered=True), observation(), CROPS)
        self.assertEqual(f['keep_water'], 0)
        self.assertEqual(f['defer_eligible'], 0)

    def test_ongoing_regular_no_water_bonus(self):
        f = features(plant('TOMATO', planted=13), observation(), CROPS)
        self.assertEqual(f['production_due_next_refresh'], 1)
        self.assertEqual(f['next_units_delta'], 0)

    def test_ongoing_fertile_bonus(self):
        f = features(plant('TOMATO', planted=13, fertile=20), observation(), CROPS)
        self.assertEqual(f['next_units_delta'], 1)
        self.assertEqual(f['keep_water'], 1)

    def test_fertile_cap(self):
        f = features(plant('TOMATO', planted=13, fertile=20, units=4), observation(), CROPS)
        self.assertEqual(f['defer_eligible'], 1)

    def test_nonproduction_night(self):
        f = features(plant('STRAWBERRY', planted=10, fertile=20), observation(), CROPS)
        self.assertEqual(f['production_due_next_refresh'], 0)

    def test_end_production_sets_expiry(self):
        t = plant('TOMATO', planted=10, units=1, watered=True)
        self.assertEqual(next_refresh(t, 20, 23, CROPS)['max_lifespan_step'], 528)

    def test_counter_changes(self):
        self.assertEqual(next_refresh(plant(), 20, 23, CROPS)['consecutive_unwatered'], 1)
        self.assertEqual(next_refresh(plant(), 20, 23, CROPS, True)['consecutive_unwatered'], 0)

    def test_decay_before_refresh(self):
        t = plant(units=1, life=503, planted=10)
        self.assertEqual(next_refresh(t, 20, 23, CROPS), {'kind': 'WEED'})

    def test_decay_phase_alignment(self):
        t = plant(life=480)
        self.assertEqual(decay_ticks(t, 481, 503), 11)
        self.assertEqual(decay_ticks(t, 480, 503), 12)

    def test_final_day_no_refresh(self):
        f = features(plant(planted=29), observation(29, 22), CROPS)
        self.assertEqual(f['refresh_available'], 0)
        self.assertEqual(f['defer_eligible'], 0)

    def test_clocks(self):
        for key, value in [('hour', 24), ('day', -1), ('step', True), ('step', 480.0)]:
            o = observation()
            o[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                clock(o)

    def test_null_step(self):
        o = observation()
        o['step'] = None
        self.assertEqual(clock(o), 480)

    def test_mutation(self):
        t = plant()
        o = observation(tile=t)
        before = deepcopy((t, o))
        features(t, o, CROPS)
        extract(o, GAME)
        self.assertEqual((t, o), before)

    def test_missing_field(self):
        t = plant()
        del t['consecutive_unwatered']
        with self.assertRaises(KeyError):
            features(t, observation(), CROPS)

    def test_invalid_yield(self):
        for n in [-1, 1.5, float('nan'), True]:
            with self.subTest(n=n), self.assertRaises(ValueError):
                features(plant(units=n), observation(), CROPS)

    def test_future_plant(self):
        with self.assertRaises(ValueError):
            features(plant(planted=21), observation(), CROPS)

    def test_unknown_crop(self):
        with self.assertRaises(ValueError):
            features(plant('RICE'), observation(), CROPS)

    def test_extra_metadata_ignored(self):
        o = observation(tile=plant())
        a = extract(o, GAME)
        o.update(seed=3, reward=1000000000.0, future_shops=['X'])
        o['private'] = {'hidden_test': 999}
        self.assertEqual(a, extract(o, GAME))

    def test_opponent_does_not_drive_gate(self):
        o = observation(tile=plant())
        a = extract(o, GAME)
        o['farms'][1]['money'] = 1000000000000.0
        self.assertEqual(a, extract(o, GAME))

    def test_unlimited_worker_aggregate(self):
        o = observation(tile=plant())
        o['farms'][0]['hands'] = [[4, 4]] * 12
        self.assertEqual(extract(o, GAME)[1]['workers'], 13)

    def test_empty(self):
        r, s = extract(observation(), GAME)
        self.assertEqual(r, [])
        self.assertEqual(len(s), len(SUMMARY_FIELDS))

    def test_quote_rejects_nonfinite(self):
        o = observation()
        o['market']['prices']['WHEAT'] = float('nan')
        with self.assertRaises(ValueError):
            features(plant(), o, CROPS)

    def test_decay_and_survival_sweep(self):
        for crop, p in CROPS.items():
            for age in range(p['max_yield_day'] + 2):
                for dry in (0, 1):
                    for fertile in (-1, 20):
                        t = plant(crop, 20 - age, units=p['max_yield'] - 1, dry=dry, fertile=fertile)
                        f = features(t, observation(), CROPS)
                        with self.subTest(crop=crop, age=age, dry=dry, fertile=fertile):
                            if f['defer_eligible']:
                                self.assertEqual(f['water_bonus_now'], 0)
                                self.assertEqual(f['survival_gain'], 0)
                                self.assertLessEqual(f['next_units_delta'], 0)
                            self.assertGreaterEqual(f['next_units_delta'], 0)
