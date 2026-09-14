import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from copy import deepcopy
import math
from types import SimpleNamespace
from timing_features import clock,known_demand,sale_path,extract,select_action,FinalSalePolicy

PRODUCTS=['WHEAT','CARROT','TOMATO','STRAWBERRY','MELON','EGG','MILK','WOOL','FERTILIZER']

class FixtureGame:
    """Explicit test double: only wheat reproduces the documented exact curve."""
    PRODUCTS=PRODUCTS
    SHOPS={'PIZZA_SHOP':['MILK','TOMATO','WHEAT'],'PET_CAFE':['CARROT'],'YARN_STORE':['WOOL']}
    TOWN_CENTER_PRODUCTS=PRODUCTS[:-1]
    MARKET_PARAMS={'registered':True}
    @staticmethod
    def _resolve_market_params(p):return p or FixtureGame.MARKET_PARAMS
    @staticmethod
    def market_price(item,inventory):
        if item=='WHEAT':
            x=abs(inventory-10000)
            price=25+20*math.sqrt(x/400) if inventory<10000 else 25-5*math.log1p(x)/math.log(401)
            return max(1,int(round(price)))
        return max(1,100-(inventory-10000))

def obs(step=716):
    g=FixtureGame()
    return {'step':step,'day':step//24,'hour':step%24,'market':{'inventory':{p:10000 for p in PRODUCTS},
          'prices':{p:g.market_price(p,10000) for p in PRODUCTS}},'town':{'unlocked_shops':['PIZZA_SHOP','PIZZA_SHOP','PET_CAFE']}}

def actions():
    c={'farmer':['DROP'],'hands':[['PASS']],'market':[['SELL','WHEAT',1]]}
    a=deepcopy(c);a['market']=[['SELL','WHEAT',2]]
    return c,a

class TestTiming(unittest.TestCase):
    def test_clock_none(self):
        x=obs();x['step']=None;self.assertEqual(clock(x),716)
    def test_clock_missing(self):
        x=obs();x.pop('step');self.assertEqual(clock(x),716)
    def test_clock_conflict(self):
        x=obs();x['step']=715
        with self.assertRaises(ValueError):clock(x)
    def test_clock_terminal_rejected(self):
        with self.assertRaises(ValueError):clock(obs(719))
    def test_clock_boolean_rejected(self):
        x=obs();x['day']=True
        with self.assertRaises(ValueError):clock(x)
    def test_clock_fractional_rejected(self):
        x=obs();x['hour']=20.0
        with self.assertRaises(ValueError):clock(x)
    def test_day29_only(self):
        with self.assertRaises(ValueError):extract(obs(10),{'shed':{}},FixtureGame())
    def test_demand_after_current_market(self):self.assertEqual(known_demand(FixtureGame(),['PIZZA_SHOP'],'TOMATO',716,1),1)
    def test_no_event(self):self.assertEqual(known_demand(FixtureGame(),['PIZZA_SHOP'],'TOMATO',717,1),0)
    def test_duplicates(self):self.assertEqual(known_demand(FixtureGame(),['PIZZA_SHOP']*2,'TOMATO',716,1),2)
    def test_specialist_multiplier(self):self.assertEqual(known_demand(FixtureGame(),['PET_CAFE'],'CARROT',716,1),2)
    def test_center(self):self.assertEqual(known_demand(FixtureGame(),[],'TOMATO',696,1),1)
    def test_fertilizer_no_center(self):self.assertEqual(known_demand(FixtureGame(),[],'FERTILIZER',696,1),0)
    def test_unknown_shop(self):
        with self.assertRaises(ValueError):known_demand(FixtureGame(),['unknown'],'WHEAT',716,1)
    def test_negative_horizon(self):
        with self.assertRaises(ValueError):known_demand(FixtureGame(),[],'WHEAT',716,-1)
    def test_zero_horizon(self):self.assertEqual(known_demand(FixtureGame(),['PIZZA_SHOP'],'WHEAT',716,0),0)
    def test_wheat_previous_regression(self):
        self.assertEqual(FixtureGame.market_price('WHEAT',1_000_000),13)
        self.assertEqual(sale_path('WHEAT',1_000_000,2,FixtureGame.market_price),(26.,1_000_002))
    def test_floor_supply_does_not_grow(self):self.assertEqual(sale_path('x',100,4,lambda p,i:1),(4.,100))
    def test_variable_price(self):self.assertEqual(sale_path('x',0,4,lambda p,i:max(1,3-i)),(7.,2))
    def test_empty_sale(self):self.assertEqual(sale_path('x',0,0,lambda p,i:3),(0.,0))
    def test_negative_inventory_allowed(self):self.assertEqual(sale_path('x',-2,2,lambda p,i:2),(4.,0))
    def test_negative_quantity(self):
        with self.assertRaises(ValueError):sale_path('x',1,-1,lambda p,i:2)
    def test_fractional_quantity(self):
        with self.assertRaises(ValueError):sale_path('x',1,1.3,lambda p,i:2)
    def test_invalid_quote(self):
        with self.assertRaises(ValueError):sale_path('x',1,1,lambda p,i:float('nan'))
    def test_schema(self):self.assertEqual(len(extract(obs(),{'shed':{}},FixtureGame())),120)
    def test_terminal_masks(self):
        f=extract(obs(718),{'shed':{'TOMATO':4}},FixtureGame());self.assertEqual(f['sale_timing.last_callback'],1)
        self.assertEqual(f['sale_timing.TOMATO.h1.available'],0)
        self.assertEqual(f['sale_timing.TOMATO.h1.conditional_holding_premium'],0)
    def test_mask_not_false_negative_value(self):
        f=extract(obs(717),{'shed':{'TOMATO':4}},FixtureGame())
        self.assertEqual(f['sale_timing.TOMATO.h1.available'],1)
        self.assertEqual(f['sale_timing.TOMATO.h4.available'],0)
    def test_holding_premium(self):
        f=extract(obs(),{'shed':{'TOMATO':4}},FixtureGame())
        self.assertEqual(f['sale_timing.TOMATO.h1.known_demand_units'],2)
        self.assertEqual(f['sale_timing.TOMATO.h1.conditional_holding_premium'],8)
    def test_input_unchanged(self):
        o=obs();p={'shed':{'TOMATO':4}};before=deepcopy((o,p));extract(o,p,FixtureGame());self.assertEqual((o,p),before)
    def test_hidden_extra_metadata_unused(self):
        o=obs();f=extract(o,{'shed':{}},FixtureGame());o.update(seed=99,reward=123,opponent_private={'gold':1})
        self.assertEqual(f,extract(o,{'shed':{}},FixtureGame()))
    def test_price_drift_rejected(self):
        o=obs();o['market']['prices']['WHEAT']=999
        with self.assertRaises(ValueError):extract(o,{'shed':{}},FixtureGame())
    def test_param_drift_rejected(self):
        o=obs();o['market']['params']={'custom':1}
        with self.assertRaises(ValueError):extract(o,{'shed':{}},FixtureGame())
    def test_prefix_identity_all_steps(self):
        c,a=actions()
        for s in range(718):self.assertEqual(select_action(obs(s),c,a),c)
    def test_final_action(self):
        c,a=actions();self.assertEqual(select_action(obs(718),c,a),a)
    def test_gate_returns_copy(self):
        c,a=actions();out=select_action(obs(718),c,a);out['market'][0][2]=50;self.assertEqual(a['market'][0][2],2)
    def test_farm_intervention_rejected(self):
        c,a=actions();a['farmer']=['PASS']
        with self.assertRaises(ValueError):select_action(obs(),c,a)
    def test_non_sell_intervention_rejected(self):
        c,a=actions();a['market'].append(['HIRE'])
        with self.assertRaises(ValueError):select_action(obs(),c,a)
    def test_final_non_sell_rejected(self):
        c,a=actions();c['market'].append(['HIRE']);a['market'].append(['HIRE'])
        with self.assertRaises(ValueError):select_action(obs(718),c,a)
    def test_order_limit(self):
        c,a=actions();a['market']*=11
        with self.assertRaises(ValueError):select_action(obs(718),c,a)
    def test_zero_negative_control(self):
        c,a=actions();self.assertEqual(select_action(obs(718),c,c),c)
    def test_wrapper_uses_control_memory(self):
        # Explicit actor double; verifies wrapper wiring, not real callback policy.
        class Actor:
            def __init__(self):self.last_diagnostics={};self.seen=[]
            def __call__(self,o):
                self.seen.append(o['step']);c,a=actions();self.last_diagnostics={'aligned_action':a};return c
        p=FinalSalePolicy.__new__(FinalSalePolicy);p.base=Actor();p.last_diagnostics={}
        self.assertEqual(p(obs(717)),actions()[0]);self.assertEqual(p(obs(718)),actions()[1]);self.assertEqual(p.base.seen,[717,718])
