"""Fast deterministic tests; synthetic states are not performance evidence."""
from copy import deepcopy
import math
import unittest
from workforce_features import Rules, canonical_observation, extract_workforce, shed_distance

RULES = Rules({"WHEAT":2, "TOMATO":8}, {"GOOSE":"EGG", "COW":"MILK"})

def fixture(hands=0, other_hands=0, player=0, day=8, hour=4):
    def farm(n):
        tiles = [[None for _ in range(10)] for _ in range(10)]
        tiles[1][2] = {"kind":"PLANT","crop":"WHEAT","planted_day":max(0,day-2),
                       "yield_units":3,"watered_today":False,"consecutive_unwatered":1}
        tiles[6][7] = {"kind":"COOP","animal":"GOOSE","yield_units":2,
                       "fed_today":False,"consecutive_unfed":1,"cared_today":False}
        tiles[3][3] = {"kind":"WEED"}
        return {"money":1000,"tiles":tiles,"farmer":[4,4],
                "hands":[[i%10,(i//10)%10] for i in range(n)],
                "unlocked_quadrants":["NW"],"hires_today":n}
    farms = [farm(hands), farm(other_hands)]
    own_n = len(farms[player]["hands"])
    return {"player":player,"step":day*24+hour,"day":day,"hour":hour,
            "farms":farms,"market":{"inventory":{},"prices":{}},"town":{"unlocked_shops":[]},
            "private":{"shed":{"WHEAT":5},"seeds":{},"inventories":[{} for _ in range(own_n+1)]}}

class WorkforceTests(unittest.TestCase):
    def test_baseline(self):
        r=extract_workforce(fixture(), RULES)
        self.assertEqual(r.state['own.worker_count'],1)
        self.assertEqual(len(r.state),124)
    def test_large_workforces(self):
        for n in (0,1,3,4,12,32,100):
            with self.subTest(n=n):
                r=extract_workforce(fixture(n,n),RULES)
                self.assertEqual(len(r.workers),2*(n+1))
                self.assertEqual(r.state['own.worker_count'],n+1)
    def test_both_seats(self):
        for p in (0,1):
            r=extract_workforce(fixture(4,12,player=p),RULES)
            self.assertEqual(r.state['own.worker_count'],(5,13)[p])
    def test_fixed_state_schema(self):
        a=extract_workforce(fixture(),RULES).state
        b=extract_workforce(fixture(12,32),RULES).state
        self.assertEqual(set(a),set(b))
    def test_no_input_mutation(self):
        obs=fixture(12,4); original=deepcopy(obs)
        extract_workforce(obs,RULES)
        self.assertEqual(obs,original)
    def test_finite_vector(self):
        self.assertTrue(all(math.isfinite(v) for v in extract_workforce(fixture(12),RULES).state.values()))
    def test_metadata_ignored(self):
        obs=fixture(); expected=extract_workforce(obs,RULES)
        obs.update(reward=float('nan'),seed=999, future=object(), opponent_private=object())
        self.assertEqual(expected,extract_workforce(obs,RULES))
    def test_opponent_nested_private_ignored(self):
        obs=fixture(); expected=extract_workforce(obs,RULES)
        obs['farms'][1]['shed']=object();obs['farms'][1]['inventories']=object()
        self.assertEqual(expected,extract_workforce(obs,RULES))
    def test_opponent_inventory_unknown(self):
        r=extract_workforce(fixture(3,12),RULES)
        self.assertTrue(all(w['carried_units'] is None and w['inventory_observed']==0 for w in r.workers if w['side']=='opponent'))
    def test_none_step(self):
        o=fixture(player=1);o['step']=None
        self.assertEqual(canonical_observation(o)['step'],196)
    def test_missing_step(self):
        o=fixture();o.pop('step');self.assertEqual(canonical_observation(o)['step'],196)
    def test_conflicting_clock(self):
        o=fixture();o['step']+=1
        with self.assertRaisesRegex(ValueError,'Conflicting'):extract_workforce(o,RULES)
    def test_final_decision(self):
        r=extract_workforce(fixture(day=29,hour=22),RULES)
        self.assertEqual(r.state['time.remaining_actions_today'],1)
    def test_terminal_not_callback(self):
        with self.assertRaises(ValueError):extract_workforce(fixture(day=29,hour=23),RULES)
    def test_inventory_alignment_short(self):
        o=fixture(4);o['private']['inventories'].pop()
        with self.assertRaisesRegex(ValueError,'alignment'):extract_workforce(o,RULES)
    def test_inventory_alignment_long(self):
        o=fixture();o['private']['inventories'].append({})
        with self.assertRaisesRegex(ValueError,'alignment'):extract_workforce(o,RULES)
    def test_board_size(self):
        o=fixture();o['farms'][0]['tiles'].pop()
        with self.assertRaises(ValueError):extract_workforce(o,RULES)
    def test_bad_coordinate(self):
        o=fixture();o['farms'][0]['farmer']=[10,4]
        with self.assertRaises(ValueError):extract_workforce(o,RULES)
    def test_fractional_coordinate(self):
        o=fixture();o['farms'][0]['farmer']=[1.5,4]
        with self.assertRaises(ValueError):extract_workforce(o,RULES)
    def test_negative_inventory(self):
        o=fixture();o['private']['shed']={'WHEAT':-1}
        with self.assertRaises(ValueError):extract_workforce(o,RULES)
    def test_nan_cash(self):
        o=fixture();o['farms'][0]['money']=float('nan')
        with self.assertRaises(ValueError):extract_workforce(o,RULES)
    def test_unknown_crop(self):
        o=fixture();o['farms'][0]['tiles'][1][2]['crop']='UNKNOWN'
        with self.assertRaises(ValueError):extract_workforce(o,RULES)
    def test_unknown_kind(self):
        o=fixture();o['farms'][0]['tiles'][1][2]['kind']='UNKNOWN'
        with self.assertRaises(ValueError):extract_workforce(o,RULES)
    def test_future_plant(self):
        o=fixture();o['farms'][0]['tiles'][1][2]['planted_day']=20
        with self.assertRaises(ValueError):extract_workforce(o,RULES)
    def test_maturity_gate(self):
        o=fixture();o['farms'][0]['tiles'][1][2]['planted_day']=o['day']
        r=extract_workforce(o,RULES)
        self.assertEqual(r.state['own.harvest.count'],1)
    def test_water_and_feed_urgency(self):
        r=extract_workforce(fixture(),RULES)
        self.assertEqual(r.state['own.water.urgent_count'],1)
        self.assertEqual(r.state['own.feed.urgent_count'],1)
    def test_no_tasks(self):
        o=fixture()
        for f in o['farms']:f['tiles']=[[None]*10 for _ in range(10)]
        r=extract_workforce(o,RULES)
        self.assertEqual(r.state['own.task_count'],0)
        self.assertEqual(r.workers[0]['harvest_present'],0)
    def test_same_position_legal(self):
        o=fixture(12);o['farms'][0]['hands']=[[4,4]]*12
        r=extract_workforce(o,RULES)
        self.assertEqual(r.state['own.colocated_worker_pairs'],78)
    def test_hand_permutation_invariance(self):
        o=fixture(4);o['private']['inventories']=[{'WHEAT':i} for i in range(5)]
        before=extract_workforce(o,RULES)
        o['farms'][0]['hands'].reverse();o['private']['inventories'][1:]=o['private']['inventories'][1:][::-1]
        after=extract_workforce(o,RULES)
        self.assertEqual(before.state,after.state)
        own_before=[w for w in before.workers if w['side']=='own'][1:]
        own_after=[w for w in after.workers if w['side']=='own'][1:]
        for a,b in zip(own_before,reversed(own_after)):
            self.assertEqual({k:v for k,v in a.items() if k!='worker_index'}, {k:v for k,v in b.items() if k!='worker_index'})
    def test_private_inventory_only_own(self):
        o=fixture();r1=extract_workforce(o,RULES)
        o['private']['inventories'][0]={'WHEAT':10};r2=extract_workforce(o,RULES)
        self.assertEqual({k:v for k,v in r1.state.items() if k.startswith('opponent.')},
                         {k:v for k,v in r2.state.items() if k.startswith('opponent.')})
    def test_manual_deposit_last_step(self):
        o=fixture(day=29,hour=22)
        o['farms'][0]['farmer']=[2,1]
        self.assertEqual(extract_workforce(o,RULES).state['own.harvest.manual_cash_reachable_units_bound'],0)
    def test_shed_geometry(self):
        self.assertEqual(shed_distance((4,5)),0)
        self.assertEqual(shed_distance((0,0)),8)
    def test_locked_travel_position(self):
        o=fixture();o['farms'][0]['tiles'][4][4]='LOCKED'
        extract_workforce(o,RULES)
    def test_boolean_clock_invalid(self):
        o=fixture();o['hour']=True
        with self.assertRaises(ValueError):extract_workforce(o,RULES)
    def test_wrong_flag_invalid(self):
        o=fixture();o['farms'][0]['tiles'][1][2]['watered_today']='false'
        with self.assertRaises(ValueError):extract_workforce(o,RULES)
    def test_overflow(self):
        o=fixture();o['private']['shed']={'WHEAT':95};o['private']['inventories']=[{'WHEAT':10}]
        self.assertEqual(extract_workforce(o,RULES).state['own_inventory.deposit_overflow_if_all_arrive'],5)

if __name__=='__main__':unittest.main()
