from copy import deepcopy
import unittest
from fixtures import observation,GAME
from terminal_context import extract,FIELDS

class ContextTests(unittest.TestCase):
    def context(self,o):return extract(o,GAME.PRODUCTS,GAME.market_price)
    def test_schema(self):self.assertEqual(len(self.context(observation())),12)
    def test_drop_at_final_callback_can_sell(self):
        o=observation(step=718);o['private']['inventories'][0]={'WHEAT':2}
        self.assertEqual(self.context(o)['terminal_context.individually_deliverable_carried_units'],2)
    def test_one_move_plus_drop_not_possible_at_last_callback(self):
        o=observation(step=718);o['farms'][0]['farmer']=[3,4];o['private']['inventories'][0]={'WHEAT':2}
        self.assertEqual(self.context(o)['terminal_context.deadline_blocked_carried_units'],2)
    def test_one_move_plus_drop_possible_with_two_callbacks(self):
        o=observation(step=717);o['farms'][0]['farmer']=[3,4];o['private']['inventories'][0]={'WHEAT':2}
        self.assertEqual(self.context(o)['terminal_context.individually_deliverable_carried_units'],2)
    def test_works_for_seat_one(self):
        a=observation(0);b=observation(1);self.assertEqual(self.context(a),self.context(b))
    def test_preserves_input(self):
        o=observation();old=deepcopy(o);self.context(o);self.assertEqual(o,old)
    def test_metadata_ignored(self):
        a=observation();b=deepcopy(a);b.update(reward=999,seed=42,opponent_private={'WHEAT':900})
        self.assertEqual(self.context(a),self.context(b))
    def test_extra_workers_not_truncated(self):
        o=observation();o['farms'][0]['hands']=[[4,4]]*12;o['private']['inventories']=[{'WHEAT':1}]*13
        self.assertEqual(self.context(o)['terminal_context.workers_with_product_cargo'],13)
    def test_worker_inventory_alignment(self):
        o=observation();o['private']['inventories'].append({})
        with self.assertRaises(ValueError):self.context(o)
    def test_shed_overflow_diagnostic(self):
        o=observation();o['private']['shed']['WHEAT']=99;o['private']['inventories'][0]={'WHEAT':4}
        self.assertEqual(self.context(o)['terminal_context.optimistic_delivery_overflow_units'],3)
    def test_nonsellable_inventory_affects_capacity(self):
        o=observation();o['private']['shed']['COW']=99;o['private']['inventories'][0]={'COW':3}
        d=self.context(o);self.assertEqual(d['terminal_context.optimistic_delivery_overflow_units'],2)
        self.assertEqual(d['terminal_context.carried_product_units'],0)
    def test_negative_inventory_rejected(self):
        o=observation();o['private']['inventories'][0]={'WHEAT':-1}
        with self.assertRaises(ValueError):self.context(o)
    def test_bad_position_rejected(self):
        o=observation();o['farms'][0]['farmer']=[99,1]
        with self.assertRaises(ValueError):self.context(o)
    def test_out_of_scope_time_rejected(self):
        with self.assertRaises(ValueError):self.context(observation(step=719))
    def test_scenario_valuation(self):
        o=observation();o['private']['shed']['WHEAT']=2;o['private']['inventories'][0]={'WHEAT':3}
        d=self.context(o);self.assertEqual(d['terminal_context.shed_liquidation_scenario_value'],20)
        self.assertEqual(d['terminal_context.deliverable_cargo_marginal_scenario_value'],30)
