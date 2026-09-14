import unittest,math
from copy import deepcopy
from price_adapter import GAME,price,obs
from harvest_features import sale_path,marginal_value,known_demand,task_features,extract,FIELDS,SUMMARY_FIELDS,clock

class FeatureTests(unittest.TestCase):
    def test_zero_quantity(self):self.assertEqual(sale_path(GAME,'MILK',10000,0),(0.,10000,0))
    def test_wheat_large_supply_not_floor(self):self.assertEqual(price('WHEAT',1000000),13)
    def test_milk_floor_does_not_add_supply(self):self.assertEqual(sale_path(GAME,'MILK',20000,12),(12.,20000,12))
    def test_negative_inventory_supported(self):self.assertGreater(sale_path(GAME,'MILK',-1,2)[0],320)
    def test_bad_quantity(self):
        for q in (-1,True,1.5,1001):
            with self.assertRaises(ValueError):sale_path(GAME,'MILK',10000,q)
    def test_unknown_item(self):
        with self.assertRaises(ValueError):sale_path(GAME,'UNKNOWN',0,1)
    def test_bad_inventory(self):
        with self.assertRaises(ValueError):sale_path(GAME,'MILK',1.1,2)
    def test_marginal_identity(self):
        for i in GAME.PRODUCTS:
            for inv in (0,10000,10200,1000000):
                for a in (0,3,80):
                    self.assertEqual(marginal_value(GAME,i,inv,6,a),sale_path(GAME,i,inv,a+6)[0]-sale_path(GAME,i,inv,a)[0])
    def test_notional_does_not_undervalue_marginal(self):
        for i in GAME.PRODUCTS:
            self.assertLessEqual(marginal_value(GAME,i,10000,6,40),price(i,10000)*6)
    def test_backlog_reduces_value(self):self.assertLess(marginal_value(GAME,'MILK',10000,6,60),marginal_value(GAME,'MILK',10000,6,0))
    def test_duplicate_shop_consumption(self):self.assertEqual(known_demand(GAME,['YARN_STORE','YARN_STORE'],'WOOL',480,1),5)
    def test_no_demand_at_delay_zero(self):self.assertEqual(known_demand(GAME,['YARN_STORE'],'WOOL',480,0),0)
    def test_demand_phase(self):self.assertEqual(known_demand(GAME,['PIZZA_SHOP'],'MILK',481,3),0)
    def test_demand_at_endpoint_excluded(self):self.assertEqual(known_demand(GAME,['PIZZA_SHOP'],'MILK',481,4),1)
    def test_fertilizer_no_center(self):self.assertEqual(known_demand(GAME,[],'FERTILIZER',480,1),0)
    def test_unknown_shop(self):
        with self.assertRaises(ValueError):known_demand(GAME,['HIDDEN_SHOP'],'MILK',0,2)
    def test_feature_schema(self):
        rows,summary=extract(obs(),GAME);self.assertEqual(len(rows),1);self.assertEqual(set(rows[0])-{'x','y','item','kind'},set(FIELDS));self.assertEqual(set(summary),set(SUMMARY_FIELDS))
    def test_no_mutation(self):
        o=obs();before=deepcopy(o);extract(o,GAME);self.assertEqual(o,before)
    def test_metadata_ignored(self):
        o=obs();result=extract(o,GAME);o.update(seed=999,reward=99999,next_action=['HARVEST']);self.assertEqual(extract(o,GAME),result)
    def test_opponent_privates_not_read(self):
        o=obs();r=extract(o,GAME);o['farms'][1]={'deliberately':'opaque'};self.assertEqual(extract(o,GAME),r)
    def test_missing_clock_derived(self):
        o=obs();o.pop('step');self.assertEqual(clock(o),480)
    def test_conflicting_clock(self):
        o=obs();o['step']=1
        with self.assertRaises(ValueError):extract(o,GAME)
    def test_final_delay_mask(self):
        r=extract(obs(29,22),GAME)[0][0];self.assertEqual(r['delivery_scenario_available'],0);self.assertEqual(r['demand_only_marginal_value'],0)
    def test_no_cross_night_hands_extrapolation(self):self.assertEqual(extract(obs(20,23),GAME)[0][0]['delivery_scenario_available'],0)
    def test_current_shed_same_product_only(self):
        o=obs();r=extract(o,GAME)[0][0];o['private']['shed']['MILK']=80;self.assertEqual(extract(o,GAME)[0][0]['marginal_value_after_shed'],r['marginal_value_after_shed'])
    def test_nondefault_market_refused(self):
        o=obs();o['market']['params']={'MILK':{'base':1}}
        with self.assertRaises(ValueError):extract(o,GAME)
    def test_wrong_quote_refused(self):
        o=obs();o['market']['prices']['TOMATO']=0
        with self.assertRaises(ValueError):extract(o,GAME)
    def test_empty_board(self):
        o=obs();o['farms'][0]['tiles'][4][4]=None;rows,s=extract(o,GAME);self.assertEqual(rows,[]);self.assertEqual(s['harvest_tasks'],0)
    def test_more_than_three_hands_extractor(self):
        o=obs();o['farms'][0]['hands']=[[x%10,0] for x in range(20)];self.assertEqual(len(extract(o,GAME)[0]),1)
    def test_animal_task(self):
        o=obs();o['farms'][0]['tiles'][4][4]={'kind':'PASTURE','animal':'COW','yield_units':6};self.assertEqual(extract(o,GAME)[0][0]['item'],'MILK')
    def test_immature_crop_excluded(self):
        o=obs();o['farms'][0]['tiles'][4][4]['planted_day']=19;self.assertEqual(extract(o,GAME)[0],[])
    def test_unavailable_single_yield_excluded(self):
        o=obs();o['farms'][0]['tiles'][4][4].update(crop='WHEAT',planted_day=18);self.assertEqual(extract(o,GAME)[0],[])
    def test_marginal_identity_decomposition(self):
        o=obs();o['private']['shed']['TOMATO']=20;r=extract(o,GAME)[0][0]
        self.assertEqual(r['within_lot_price_impact']+r['backlog_price_impact'],r['total_quote_overstatement'])
    def test_finite_outputs(self):
        self.assertTrue(all(math.isfinite(v) for row in extract(obs(),GAME)[0] for k,v in row.items() if k in FIELDS))
