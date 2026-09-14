"""Isolated callback wiring tests with explicitly artificial repository dependencies."""
from copy import deepcopy
import sys
from types import ModuleType,SimpleNamespace
import unittest
from unittest.mock import patch
from cash_features import terminal_market_rule
from callback import CashPolicy,apply_farm_actions
from fixtures import fixture,ToyGame,value


def dependencies():
    class Base:
        def __init__(self,arm):self.arm=arm;self.last_step=None;self.player=None
        @classmethod
        def from_state_dict(cls,s):
            x=cls(s['arm']);x.last_step=s['last_step'];x.player=s['player'];return x
        def __call__(self,obs):
            if self.last_step is not None and obs['step']!=self.last_step+1:raise ValueError('clock')
            self.last_step=obs['step'];self.player=obs['player']
            a={'farmer':['PASS'],'hands':[['PASS'] for _ in obs['farms'][obs['player']]['hands']],'market':[]}
            if obs['day']==29:a['market']=terminal_market_rule(obs,ToyGame,value)
            return a
    values={
      'kaggriculture_terminal.feed_policy':{'FeedPolicy':Base},
      'kaggriculture_research.environment':{'game':ToyGame},
      'kaggriculture_staffing.features':{'canonical_observation':lambda x:deepcopy(x)},
      'kaggriculture_livestock.features':{'fertilizer_value':value},
      'kaggriculture_terminal.routing':{'menus':lambda obs:([obs],{'room':100})},
      'kaggriculture_runtime.routing':{'assign':lambda menu,room,obs:([
          SimpleNamespace(actions=(('DROP',),)) for _ in range(1+len(obs['farms'][obs['player']]['hands']))],{'joint_utility':0})},
    }
    modules={}
    for name,attrs in values.items():
        mod=ModuleType(name);mod.__dict__.update(attrs);modules[name]=mod
        parent=name.rsplit('.',1)[0]
        if parent not in modules:modules[parent]=ModuleType(parent);modules[parent].__path__=[]
    return modules


class CallbackWiringTests(unittest.TestCase):
    def test_only_market_changes_in_coordinated_case(self):
        obs=fixture();obs['private']['inventories'][0]={'WHEAT':3}
        with patch.dict(sys.modules,dependencies()):
            c=CashPolicy('coordinated','control')(obs);a=CashPolicy('coordinated','aligned')(obs)
        self.assertEqual(c['farmer'],a['farmer']);self.assertEqual(c['hands'],a['hands'])
        self.assertEqual(c['market'],[]);self.assertEqual(a['market'],[['SELL','WHEAT',3]])
    def test_sequential_negative_control_unchanged(self):
        obs=fixture();obs['private']['inventories'][0]={'WHEAT':3}
        with patch.dict(sys.modules,dependencies()):
            self.assertEqual(CashPolicy('sequential','control')(obs),CashPolicy('sequential','aligned')(obs))
    def test_preterminal_negative_control_unchanged(self):
        obs=fixture(step=695)
        with patch.dict(sys.modules,dependencies()):
            a=CashPolicy('coordinated','aligned');c=CashPolicy('coordinated','control')
            self.assertEqual(a(obs),c(obs));self.assertFalse(a.last_diagnostics['active'])
    def test_callback_input_not_modified(self):
        obs=fixture();obs['private']['inventories'][0]={'WHEAT':3};old=deepcopy(obs)
        with patch.dict(sys.modules,dependencies()):CashPolicy('coordinated','aligned')(obs)
        self.assertEqual(obs,old)
    def test_callback_unknown_arm_rejected(self):
        with self.assertRaises(ValueError):CashPolicy('unknown')
    def test_clock_state_roundtrip(self):
        with patch.dict(sys.modules,dependencies()):
            a=CashPolicy();a.prime_recorded_clock(709,0);a(fixture(step=710))
            self.assertEqual(a.base.last_step,710)
    def test_skipped_causal_step_rejected(self):
        with patch.dict(sys.modules,dependencies()):
            a=CashPolicy();a.prime_recorded_clock(709,0)
            with self.assertRaises(ValueError):a(fixture(step=711))
    def test_stale_rule_is_detected(self):
        obs=fixture();obs['private']['shed']={'WHEAT':3}
        modules=dependencies()
        original=modules['kaggriculture_terminal.feed_policy'].FeedPolicy
        class Incorrect(original):
            def __call__(self,obs):return {'farmer':['PASS'],'hands':[],'market':[]}
        modules['kaggriculture_terminal.feed_policy'].FeedPolicy=Incorrect
        with patch.dict(sys.modules,modules):
            with self.assertRaisesRegex(ValueError,'reproduce frozen'):CashPolicy()(obs)
