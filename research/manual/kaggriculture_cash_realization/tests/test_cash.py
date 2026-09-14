import copy
import math
import unittest
from cash_features import (count,counts,requested_sales,solo_sale_value,
    terminal_market_rule,extract_cash_features,non_sell_orders,PRODUCT_FIELDS,GLOBAL_FIELDS)
from fixtures import fixture,price,value,ToyGame,PRODUCTS

class CashFeatureTests(unittest.TestCase):
    def setUp(self):
        self.obs=fixture();self.post=copy.deepcopy(self.obs['private'])
        self.post['shed']={'WHEAT':3}
    def extract(self,a=(),b=(('SELL','WHEAT',3),)):
        return extract_cash_features(self.obs,self.post,list(a),list(b),PRODUCTS,price)
    def test_schema(self):self.assertEqual(len(self.extract().values),158)
    def test_product_schema(self):self.assertEqual(set(self.extract().products[0]),{'product',*PRODUCT_FIELDS})
    def test_new_deposit_exposed(self):self.assertEqual(self.extract().values['cash.uncovered_sellable_units'],3)
    def test_incremental_revenue(self):self.assertEqual(self.extract().values['cash.solo_revenue_delta'],72)
    def test_partial_source_coverage(self):self.assertEqual(self.extract([['SELL','WHEAT',1]]).values['cash.uncovered_sellable_units'],2)
    def test_over_requested_is_capped(self):self.assertEqual(self.extract([['SELL','WHEAT',100]]).values['cash.uncovered_sellable_units'],0)
    def test_equal_orders_zero_effect(self):self.assertEqual(self.extract([['SELL','WHEAT',3]]).values['cash.solo_revenue_delta'],0)
    def test_negative_effect_preserved(self):self.assertEqual(self.extract([['SELL','WHEAT',3]],[]).values['cash.solo_revenue_delta'],-72)
    def test_final_callback_indicator(self):
        self.obs['step']=718;self.obs['hour']=22
        self.assertEqual(self.extract().values['cash.final_callback'],1)
    def test_non_final_callback(self):self.assertEqual(self.extract().values['cash.final_callback'],0)
    def test_input_immutability(self):
        before=copy.deepcopy((self.obs,self.post));self.extract();self.assertEqual((self.obs,self.post),before)
    def test_reward_metadata_ignored(self):
        baseline=self.extract().values;self.obs.update(reward=1e8,seed=999,future={'foo':math.nan},opponent_private={'secret':100})
        self.assertEqual(self.extract().values,baseline)
    def test_unknown_private_not_consulted(self):
        self.obs['farms'][1]['private']={'fake':math.nan}
        self.assertEqual(self.extract().values['cash.solo_revenue_delta'],72)
    def test_clock_conflict(self):
        self.obs['hour']=1
        with self.assertRaises(ValueError):self.extract()
    def test_terminal_state_rejected(self):
        self.obs['step']=719;self.obs['hour']=23
        with self.assertRaises(ValueError):self.extract()
    def test_early_day_rejected(self):
        self.obs['day']=28
        with self.assertRaises(ValueError):self.extract()
    def test_shed_overflow_rejected(self):
        self.post['shed']['WHEAT']=101
        with self.assertRaises(ValueError):self.extract()
    def test_counts_negative_rejected(self):
        with self.assertRaises(ValueError):counts({'WHEAT':-1},'test')
    def test_counts_fraction_rejected(self):
        with self.assertRaises(ValueError):count(1.2,'test')
    def test_counts_boolean_rejected(self):
        with self.assertRaises(ValueError):count(True,'test')
    def test_counts_nan_rejected(self):
        with self.assertRaises(ValueError):count(math.nan,'test')
    def test_counts_infinite_rejected(self):
        with self.assertRaises(ValueError):count(math.inf,'test')
    def test_price_floor_not_accumulating(self):
        seen=[]
        self.assertEqual(solo_sale_value('WHEAT',42,4,lambda item,inv:seen.append(inv) or 1),4)
        self.assertEqual(seen,[42]*4)
    def test_negative_market_inventory_allowed(self):self.assertEqual(solo_sale_value('WHEAT',-1,3,price),75)
    def test_nonfinite_price_rejected(self):
        with self.assertRaises(ValueError):solo_sale_value('WHEAT',0,1,lambda *args:math.nan)
    def test_zero_price_rejected(self):
        with self.assertRaises(ValueError):solo_sale_value('WHEAT',0,1,lambda *args:0)
    def test_buy_not_silently_modelled_as_sell(self):
        with self.assertRaises(ValueError):requested_sales([['BUY_PRODUCT','WHEAT',1]],PRODUCTS)
    def test_duplicate_sell_rejected(self):
        with self.assertRaises(ValueError):requested_sales([['SELL','WHEAT',1]]*2,PRODUCTS)
    def test_zero_sell_rejected(self):
        with self.assertRaises(ValueError):requested_sales([['SELL','WHEAT',0]],PRODUCTS)
    def test_unknown_item_rejected(self):
        with self.assertRaises(ValueError):requested_sales([['SELL','SECRET',1]],PRODUCTS)
    def test_too_many_orders_rejected(self):
        with self.assertRaises(ValueError):requested_sales([['HIRE']]*11,PRODUCTS)
    def test_multiple_hires_rejected(self):
        with self.assertRaises(ValueError):requested_sales([['HIRE']]*2,PRODUCTS)
    def test_hiring_is_not_counted_as_revenue(self):self.assertEqual(self.extract(b=[['HIRE']]).values['cash.aligned_solo_revenue'],0)
    def test_non_sell_attribution(self):self.assertEqual(non_sell_orders({'market':[['SELL','WHEAT',3],['HIRE']]}),[['HIRE']])
    def test_rule_before_terminal_rejects(self):
        self.obs['day']=28
        with self.assertRaises(ValueError):terminal_market_rule(self.obs,ToyGame,value)
    def test_rule_sells_all_without_reserves(self):
        self.obs['private']['shed']={'WHEAT':3}
        self.assertEqual(terminal_market_rule(self.obs,ToyGame,value),[['SELL','WHEAT',3]])
    def test_rule_fertilizer_reserve(self):
        self.obs['private']['shed']={'FERTILIZER':4}
        self.obs['farms'][0]['tiles'][0][0]={'kind':'PLANT','test_value':1}
        self.assertEqual(terminal_market_rule(self.obs,ToyGame,value),[['SELL','FERTILIZER',3]])
    def test_rule_carried_manure_satisfies_reserve(self):
        self.obs['private']['shed']={'FERTILIZER':4};self.obs['private']['inventories'][0]={'FERTILIZER':1}
        self.obs['farms'][0]['tiles'][0][0]={'kind':'PLANT','test_value':1}
        self.assertEqual(terminal_market_rule(self.obs,ToyGame,value),[['SELL','FERTILIZER',4]])
    def test_rule_last_eight_liquidates_reserve(self):
        self.obs['step']=711;self.obs['hour']=15;self.obs['private']['shed']={'FERTILIZER':4}
        self.obs['farms'][0]['tiles'][0][0]={'kind':'PLANT','test_value':1}
        self.assertEqual(terminal_market_rule(self.obs,ToyGame,value),[['SELL','FERTILIZER',4]])
    def test_hire_same_early_window(self):
        obs=fixture(step=696);self.assertEqual(terminal_market_rule(obs,ToyGame,value),[['HIRE']])
    def test_no_hire_after_window(self):
        obs=fixture(step=702);self.assertEqual(terminal_market_rule(obs,ToyGame,value),[])
    def test_no_hire_with_three_hands(self):
        obs=fixture(step=696,hands=3);self.assertEqual(terminal_market_rule(obs,ToyGame,value),[])
    def test_no_hire_without_cash(self):
        obs=fixture(step=696);obs['farms'][0]['money']=0;self.assertEqual(terminal_market_rule(obs,ToyGame,value),[])
    def test_nine_products_and_hire_fit_ten_orders(self):
        obs=fixture(step=696);obs['private']['shed']={i:1 for i in PRODUCTS}
        self.assertEqual(len(terminal_market_rule(obs,ToyGame,value)),10)
    def test_rule_same_both_seats(self):
        a=fixture(seat=0);b=fixture(seat=1)
        self.assertEqual(terminal_market_rule(a,ToyGame,value),terminal_market_rule(b,ToyGame,value))
