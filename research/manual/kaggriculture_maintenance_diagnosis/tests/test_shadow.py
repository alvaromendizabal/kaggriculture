import unittest
from copy import deepcopy
from replay_diagnosis import shadow_turn
from helpers import toy_game,observation
class ShadowTests(unittest.TestCase):
    def args(self):
        o=observation();o['farms'][0]['tiles'][1][1]=None
        b=deepcopy(o);b['player']=1
        a=[{'farmer':['PASS'],'hands':[],'market':[]},{'farmer':['PASS'],'hands':[],'market':[]}]
        return [o,b],a
    def test_sales_actual_not_request(self):
        obs,a=self.args();a[0]['market']=[['SELL','WHEAT',100]]
        farms,trade,_=shadow_turn(obs,a,toy_game(),{},480)
        self.assertEqual(sum(x['units'] for x in trade),3);self.assertEqual(farms[0]['money'],3015)
    def test_both_players(self):
        obs,a=self.args();a[0]['market']=[['SELL','WHEAT',1]];a[1]['market']=[['SELL','WHEAT',2]]
        _,t,_=shadow_turn(obs,a,toy_game(),{},480);self.assertEqual([x['player'] for x in t],[0,1,1])
    def test_hire_cash(self):
        obs,a=self.args();a[0]['market']=[['HIRE']];f,t,_=shadow_turn(obs,a,toy_game(),{},480)
        self.assertEqual(t[0]['cash'],-1);self.assertEqual(t[0]['operation'],'HIRE')
    def test_land_cash(self):
        obs,a=self.args();a[0]['market']=[['BUY_LAND']];f,t,_=shadow_turn(obs,a,toy_game(),{},480);self.assertEqual(t[0]['cash'],-1000)
    def test_buy_seed(self):
        obs,a=self.args();a[0]['market']=[['BUY_SEED','WHEAT',2]];f,t,_=shadow_turn(obs,a,toy_game(),{},480);self.assertEqual(sum(x['cash'] for x in t),-10)
    def test_original_globals_unchanged(self):
        g=toy_game();before=dict(g._process_market.__globals__);obs,a=self.args();a[0]['market']=[['SELL','WHEAT',1]];shadow_turn(obs,a,g,{},480)
        self.assertEqual(before,g._process_market.__globals__)
    def test_inputs_not_mutated(self):
        obs,a=self.args();old=deepcopy((obs,a));shadow_turn(obs,a,toy_game(),{},480);self.assertEqual(old,(obs,a))
    def test_extra_hand_refused(self):
        obs,a=self.args();a[0]['hands']=[['PASS']]
        with self.assertRaises(ValueError):shadow_turn(obs,a,toy_game(),{},480)
