from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fixtures import fixture,ToyGame,PRODUCTS
import run_cash as runner
from callback import apply_farm_actions

class RunnerTests(unittest.TestCase):
    def test_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.gz';runner.save_cache(p,'fp',{'x':3});self.assertEqual(runner.load_cache(p,'fp'),{'x':3})
    def test_missing_cache(self):
        with tempfile.TemporaryDirectory() as d:self.assertIsNone(runner.load_cache(Path(d)/'none','fp'))
    def test_fingerprint_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.gz';runner.save_cache(p,'fp',{})
            with self.assertRaises(ValueError):runner.load_cache(p,'different')
    def test_checksum_mismatch(self):
        import gzip
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.gz';runner.save_cache(p,'fp',{})
            data=json.loads(gzip.decompress(p.read_bytes()));data['payload']={'fake':1};p.write_bytes(gzip.compress(json.dumps(data).encode()))
            with self.assertRaises(ValueError):runner.load_cache(p,'fp')
    def test_path_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):runner.contained(d,'../secret')
    def test_same_root_path(self):
        with tempfile.TemporaryDirectory() as d:self.assertEqual(runner.contained(d,'a'),Path(d)/'a')
    def test_reject_latency_max_not_average(self):
        with self.assertRaises(RuntimeError):runner.runtime_gate([{'control_callback_ms':1,'aligned_callback_ms':501}])
    def test_latency_accept_exact_limit(self):self.assertEqual(runner.runtime_gate([{'control_callback_ms':500,'aligned_callback_ms':1}])['control'],500)
    def test_atomic_write_creates_parent(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'sub'/'a.json';runner.write(p,{'ok':True});self.assertTrue(runner.read(p)['ok'])
    def test_apply_does_not_mutate(self):
        obs=fixture();obs['private']['inventories'][0]={'WHEAT':3};before=deepcopy(obs)
        after=apply_farm_actions(obs,{'farmer':['DROP'],'hands':[]},ToyGame)
        self.assertEqual(obs,before);self.assertEqual(after['private']['shed']['WHEAT'],3)
    def test_ordered_drop_capacity(self):
        obs=fixture(hands=1);obs['private']['shed']={'FERTILIZER':98};obs['private']['inventories']=[{'WHEAT':3},{'MILK':3}]
        after=apply_farm_actions(obs,{'farmer':['DROP'],'hands':[['DROP']]},ToyGame)
        self.assertEqual(after['private']['shed'],{'FERTILIZER':98,'WHEAT':2})
    def test_worker_count_mismatch(self):
        with self.assertRaises(ValueError):apply_farm_actions(fixture(hands=1),{'farmer':['PASS'],'hands':[]},ToyGame)
    def test_atomic_overplanted_seeds(self):
        obs=fixture(hands=1);obs['private']['seeds']['WHEAT']=1
        a={'farmer':['PLANT','WHEAT'],'hands':[['PLANT','WHEAT']]}
        after=apply_farm_actions(obs,a,ToyGame);self.assertEqual(after['private']['seeds']['WHEAT'],1)
    def test_evaluator_requires_same_public_state(self):
        a=fixture();b=deepcopy(a);b['player']=1;b['hour']+=1
        with self.assertRaises(ValueError):runner.isolated_transition(a,b,{}, {},ToyGame)
    def test_evaluator_requires_opposite_seat(self):
        a=fixture()
        with self.assertRaises(ValueError):runner.isolated_transition(a,a,{}, {},ToyGame)
    def test_evaluator_final_day_only(self):
        a=fixture(step=0);b=deepcopy(a);b['player']=1
        with self.assertRaises(ValueError):runner.isolated_transition(a,b,{}, {},ToyGame)
    def test_evaluator_copies_both_inputs(self):
        a=fixture();a['private']['inventories'][0]={'WHEAT':3};b=deepcopy(a);b['player']=1
        old=deepcopy((a,b));act={'farmer':['DROP'],'hands':[],'market':[['SELL','WHEAT',3]]}
        result=runner.isolated_transition(a,b,act,act,ToyGame)
        self.assertEqual((a,b),old);self.assertEqual(result[0]['day'],29)
    def test_final_reward_source_check(self):
        a=fixture(step=718);b=deepcopy(a);b['player']=1
        act={'farmer':['PASS'],'hands':[],'market':[]}
        result=runner.isolated_transition(a,b,act,act,ToyGame)
        runner.assert_source_transition(result,None,[3000.,3000.],718)
    def test_wrong_final_reward_rejected(self):
        a=fixture(step=718);b=deepcopy(a);b['player']=1;act={'farmer':['PASS'],'hands':[],'market':[]}
        result=runner.isolated_transition(a,b,act,act,ToyGame)
        with self.assertRaises(ValueError):runner.assert_source_transition(result,None,[3001.,3000.],718)
    def test_effect_labels_separate(self):
        a=fixture();b=deepcopy(a);b['player']=1;act={'farmer':['PASS'],'hands':[],'market':[]}
        result=runner.isolated_transition(a,b,act,act,ToyGame)
        self.assertEqual(runner.effects(a,result,result,PRODUCTS)['own_cash_delta'],0)
    def test_empty_bundle_works_after_failure(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'BASE',Path(d)),patch.object(runner,'OUT',Path(d)/'outputs'):
            runner.bundle()
            with zipfile.ZipFile(Path(d)/'kaggriculture_cash_realization_results.zip') as z:self.assertIn('BUNDLE_MANIFEST.json',z.namelist())
