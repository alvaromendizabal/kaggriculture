from copy import deepcopy
import math
import unittest
from opportunity_features import (extract_opportunities,route,nearest_shed,decay_units,
                                  sale_prefix,admitted_drop,incremental_value,choose,ARMS)
from fixtures import fixture,RULES,price

class Features(unittest.TestCase):
    def test_schema(self):
        r=extract_opportunities(fixture(),RULES)
        self.assertEqual(len(r.state),22)
        self.assertEqual(len(r.choices),15)
    def test_worker_sizes(self):
        for n in (0,3,4,12,32):
            r=extract_opportunities(fixture(n),RULES)
            self.assertEqual({c['worker_index'] for c in r.candidates},set(range(n+1)))
    def test_both_seats(self):
        a=extract_opportunities(fixture(seat=0),RULES)
        b=extract_opportunities(fixture(seat=1),RULES)
        self.assertEqual(a,b)
    def test_immutability(self):
        obs=fixture();before=deepcopy(obs);extract_opportunities(obs,RULES)
        self.assertEqual(obs,before)
    def test_no_hidden_inputs(self):
        obs=fixture();expected=extract_opportunities(obs,RULES)
        obs.update(reward=float('nan'),seed=object(),future_state=object(),opponent_private=object())
        obs['farms'][1].update(shed=object(),inventories=object())
        self.assertEqual(expected,extract_opportunities(obs,RULES))
    def test_null_clock(self):
        obs=fixture();obs['step']=None
        self.assertEqual(extract_opportunities(obs,RULES),extract_opportunities(fixture(),RULES))
    def test_missing_clock(self):
        obs=fixture();obs.pop('step');extract_opportunities(obs,RULES)
    def test_clock_conflict(self):
        obs=fixture();obs['step']+=1
        with self.assertRaises(ValueError):extract_opportunities(obs,RULES)
    def test_wrong_day(self):
        obs=fixture();obs.update(day=28,step=684)
        with self.assertRaises(ValueError):extract_opportunities(obs,RULES)
    def test_done_not_callback(self):
        with self.assertRaises(ValueError):extract_opportunities(fixture(hour=23),RULES)
    def test_alignment(self):
        obs=fixture();obs['private']['inventories'].pop()
        with self.assertRaises(ValueError):extract_opportunities(obs,RULES)
    def test_prices_checked(self):
        obs=fixture();obs['market']['prices']['WHEAT']+=1
        with self.assertRaises(ValueError):extract_opportunities(obs,RULES)
    def test_market_override_rejected(self):
        obs=fixture();obs['market']['params']={'WHEAT':{'above_target':2}}
        with self.assertRaises(ValueError):extract_opportunities(obs,RULES)
    def test_negative_inventory(self):
        obs=fixture();obs['private']['shed']['WHEAT']=-1
        with self.assertRaises(ValueError):extract_opportunities(obs,RULES)
    def test_capacity_checked(self):
        obs=fixture();obs['private']['shed']['WHEAT']=101
        with self.assertRaises(ValueError):extract_opportunities(obs,RULES)
    def test_maturity(self):
        obs=fixture();obs['farms'][0]['tiles'][4][4]['planted_day']=29
        r=extract_opportunities(obs,RULES)
        self.assertFalse(any(c['task_id']=='harvest:4:4' for c in r.candidates))
    def test_future_plant(self):
        obs=fixture();obs['farms'][0]['tiles'][4][4]['planted_day']=30
        with self.assertRaises(ValueError):extract_opportunities(obs,RULES)
    def test_missing_decay_field(self):
        obs=fixture();obs['farms'][0]['tiles'][4][4].pop('max_lifespan_step')
        with self.assertRaises(ValueError):extract_opportunities(obs,RULES)
    def test_last_decision_harvest_not_cash(self):
        r=extract_opportunities(fixture(hour=22),RULES)
        self.assertTrue(all(c['full_rate']==0 for c in r.candidates))
    def test_last_decision_drop_cash(self):
        obs=fixture(hands=0,hour=22);obs['private']['inventories'][0]={'WHEAT':3}
        r=extract_opportunities(obs,RULES)
        c=[c for c in r.choices if c['arm']=='full'][0]
        self.assertEqual(c['first_action'],'DROP');self.assertGreater(c['selected_rate'],0)
    def test_exact_deadline_two_actions(self):
        r=extract_opportunities(fixture(hands=0,hour=21),RULES)
        c=next(c for c in r.candidates if c['task_id']=='harvest:4:4')
        self.assertEqual(c['deadline_slack'],0);self.assertGreater(c['full_rate'],0)
    def test_no_tasks_pass(self):
        obs=fixture();obs['farms'][0]['tiles']=[[None]*10 for _ in range(10)]
        r=extract_opportunities(obs,RULES)
        self.assertTrue(all(c['first_action']=='PASS' for c in r.choices))
    def test_pass_wins_zero_tie(self):
        obs=fixture();obs['private']['shed']={'WHEAT':100}
        r=extract_opportunities(obs,RULES)
        self.assertTrue(all(c['first_action']=='PASS' for c in r.choices if c['arm']=='full'))
    def test_capacity_probe_activates(self):
        obs=fixture();obs['private']['shed']={'WHEAT':100}
        r=extract_opportunities(obs,RULES)
        self.assertGreater(r.state['probe.no_capacity.changed_first_actions'],0)
    def test_deadline_probe_activates(self):
        r=extract_opportunities(fixture(hour=22),RULES)
        self.assertGreater(r.state['probe.no_deadline.changed_first_actions'],0)
    def test_group_regret_same_first_action(self):
        r=extract_opportunities(fixture(),RULES)
        for w in (0,1,2):
            for op in ('NORTH','SOUTH','EAST','WEST'):
                vals={c['first_action_regret_rate'] for c in r.candidates if c['worker_index']==w and c['first_action']==op}
                self.assertLessEqual(len(vals),1)
    def test_finite_features(self):
        r=extract_opportunities(fixture(12),RULES)
        self.assertTrue(all(math.isfinite(v) for c in r.candidates for v in c.values() if isinstance(v,(int,float))))
    def test_negative_harvest_marginal_not_clipped(self):
        obs=fixture(hands=0);obs['private']['shed']={'FERTILIZER':93}
        obs['private']['inventories'][0]={'WHEAT':1,'MILK':5}
        r=extract_opportunities(obs,RULES)
        c=next(c for c in r.candidates if c['task_id']=='harvest:4:4')
        self.assertLess(c['marginal_harvest_revenue'],0)
    def test_locked_travel(self):
        obs=fixture();obs['farms'][0]['tiles'][3][4]='LOCKED'
        extract_opportunities(obs,RULES)
    def test_colocated_workers(self):
        obs=fixture(12);obs['farms'][0]['hands']=[[4,4]]*12
        r=extract_opportunities(obs,RULES)
        self.assertGreater(r.state['action.contested_top_tasks'],0)
    def test_choices_are_existing(self):
        r=extract_opportunities(fixture(),RULES)
        ids={c['candidate_id'] for c in r.candidates}
        self.assertTrue(all(c['candidate_id'] in ids for c in r.choices))
    def test_schema_no_workforce_dependence(self):
        self.assertEqual(set(extract_opportunities(fixture(0),RULES).state),set(extract_opportunities(fixture(12),RULES).state))
    def test_bad_arm(self):
        with self.assertRaises(ValueError):choose([], 'unknown')
    def test_rate_infeasible_is_zero(self):
        r=extract_opportunities(fixture(hour=22),RULES)
        self.assertTrue(all(c['full_rate']==0 for c in r.candidates if not c['within_deadline']))

class Mechanics(unittest.TestCase):
    def test_routes(self):
        for start in ((0,0),(4,4),(9,9)):
            for end in ((4,4),(9,0),(0,9)):
                self.assertEqual(len(route(start,end)),sum(abs(a-b) for a,b in zip(start,end)))
    def test_route_stationary(self):self.assertEqual(route((4,4),(4,4)),[])
    def test_bad_route_coordinate(self):
        with self.assertRaises(ValueError):route((10,0),(4,4))
    def test_shed_tie_stable(self):self.assertEqual(nearest_shed((0,0)),(4,4))
    def test_decay_against_loop(self):
        for step in range(696,719):
            for travel in range(15):
                for m in (-1,692,696,700,718,720):
                    tile={'kind':'PLANT','max_lifespan_step':m,'yield_units':6}
                    expected=6
                    for t in range(step,step+travel):
                        if m>=0 and t>=m and (t-m)%2==0:expected=max(0,expected-1)
                    self.assertEqual(decay_units(tile,step,travel),expected)
    def test_no_decay_on_harvest_turn(self):
        self.assertEqual(decay_units({'kind':'PLANT','max_lifespan_step':696,'yield_units':4},696,0),4)
    def test_animal_no_turn_decay(self):
        self.assertEqual(decay_units({'kind':'COOP','yield_units':4},696,10),4)
    def test_drop_order(self):
        self.assertEqual(admitted_drop({'WHEAT':3,'MILK':3},4),{'WHEAT':3,'MILK':1})
        self.assertEqual(admitted_drop({'MILK':3,'WHEAT':3},4),{'MILK':3,'WHEAT':1})
    def test_drop_zero(self):self.assertEqual(admitted_drop({'WHEAT':3},0),{})
    def test_drop_negative(self):
        with self.assertRaises(ValueError):admitted_drop({'WHEAT':-3},4)
    def test_floor_no_supply_increase(self):self.assertEqual(sale_prefix(lambda i,n:1,'WHEAT',77,10),(10,77))
    def test_sale_supply_progression(self):
        self.assertEqual(sale_prefix(lambda i,n:max(1,5-n),'WHEAT',0,7),(17,4))
    def test_incremental_value_accounts_for_shed(self):
        market={p:10000 for p in RULES.products}
        v=incremental_value({'WHEAT':4},{'WHEAT':10},market,RULES)
        self.assertEqual(v,sum(price('WHEAT',i) for i in range(10010,10014)))
    def test_unsellable_still_consumes_room(self):
        self.assertEqual(admitted_drop({'GOOSE':2,'WHEAT':4},3),{'GOOSE':2,'WHEAT':1})
    def test_negative_sale_rejected(self):
        with self.assertRaises(ValueError):sale_prefix(price,'WHEAT',10000,-1)

if __name__=='__main__':unittest.main()
