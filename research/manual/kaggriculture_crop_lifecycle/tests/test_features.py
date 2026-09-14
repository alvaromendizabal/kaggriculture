from copy import deepcopy
from types import SimpleNamespace
import unittest
from lifecycle_features import *
from mechanics import core_checks
from helpers import observation,plant,CROPS
from tests import official_refresh_excerpt as official
LAYOUT={(4,4):'TOMATO'}
class FeatureTests(unittest.TestCase):
    def test_tomato_finite_schedule(self):self.assertEqual(schedule(plant('TOMATO',0,0),CROPS),(8,9,10,11))
    def test_strawberry_finite_schedule(self):self.assertEqual(schedule(plant('STRAWBERRY',0,0),CROPS),(10,12,14,16))
    def test_single_yield_has_no_refresh_events(self):self.assertEqual(schedule(plant('WHEAT',0,0),CROPS),())
    def test_not_next_day_deferral(self):self.assertFalse(exhausted_empty(plant('TOMATO',15,0),observation(20),CROPS))
    def test_empty_spent(self):self.assertTrue(exhausted_empty(plant('TOMATO',0,0),observation(11),CROPS))
    def test_current_goods_protected(self):self.assertFalse(exhausted_empty(plant('TOMATO',0,1),observation(20),CROPS))
    def test_late_future_goods_protected(self):self.assertFalse(exhausted_empty(plant('STRAWBERRY',22,0),observation(28),CROPS))
    def test_singles_never_retired(self):self.assertFalse(exhausted_empty(plant('WHEAT',0,0),observation(20),CROPS))
    def test_unknown_crop_fail_closed(self):
        with self.assertRaises(ValueError):schedule(plant('BAD',0,0),CROPS)
    def test_future_plant_rejected(self):
        with self.assertRaises(ValueError):exhausted_empty(plant('TOMATO',21,0),observation(20),CROPS)
    def test_negative_yield_rejected(self):
        with self.assertRaises(ValueError):schedule(plant('TOMATO',0,-1),CROPS)
    def test_conflicting_clock(self):
        o=observation();o['step']=1
        with self.assertRaises(ValueError):clock(o)
    def test_missing_seat_clock_allowed(self):
        o=observation();o.pop('step');self.assertEqual(clock(o),480)
    def test_noninteger_clock(self):
        o=observation();o['hour']=True
        with self.assertRaises(ValueError):clock(o)
    def test_no_mutation_and_finite_schema(self):
        o=observation(12,tile=plant('TOMATO',0,0));before=deepcopy(o)
        r,s=extract(o,official,LAYOUT)
        self.assertEqual(o,before);self.assertEqual(len(r[0]),len(FIELDS)+4);self.assertEqual(set(s),set(SUMMARY_FIELDS))
        self.assertTrue(all(isfinite(r[0][k]) for k in FIELDS))
    def test_new_worker_counts_not_truncated_in_features(self):
        o=observation(12,tile=plant('TOMATO',0,0));o['farms'][0]['hands']=[[0,0]]*12
        self.assertEqual(extract(o,official,LAYOUT)[1]['current_workers'],13)
    def test_private_opponent_and_reward_ignored(self):
        o=observation(12,tile=plant('TOMATO',0,0));r=extract(o,official,LAYOUT)
        o['reward']=999;o['seed']=999;o['farms'][1]['private']={'secret':999};o['future_actions']=['BAD']
        self.assertEqual(r,extract(o,official,LAYOUT))
    def test_replant_window_cannot_be_extended(self):
        o=observation(22,tile=plant('TOMATO',0,0));r=extract(o,official,LAYOUT)[0][0]
        self.assertEqual(r['renewal_eligible'],0)
    def test_nonlayout_not_cleared(self):
        o=observation(12,tile=plant('TOMATO',0,0));self.assertEqual(extract(o,official,{})[0][0]['renewal_eligible'],0)
    def test_calendar_oracle_all_five_crops(self):
        r=core_checks(official);self.assertEqual(len(r),380);self.assertTrue(all(x['expected']==x['observed'] for x in r))
    def test_due_today_is_already_elapsed(self):
        o=observation(10,tile=plant('TOMATO',0,0));r=extract(o,official,LAYOUT)[0][0]
        self.assertEqual(r['scheduled_events_remaining'],1);self.assertEqual(r['callbacks_to_next_event'],24)
