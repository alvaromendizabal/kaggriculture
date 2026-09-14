from pathlib import Path
from copy import deepcopy
import gzip
import json
import tempfile
import unittest
from unittest.mock import patch
from fixtures import make_payload,observation,GAME,transition,factory
import run_continuation as r
from continuation import rollout,pair_results
from terminal_context import extract
from run_cash import assert_source_transition

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.logger=patch.object(r,'log');self.logger.start()
    def tearDown(self):self.logger.stop();self.tmp.cleanup()
    def test_atomic_json_readback(self):
        p=self.root/'a.json';r.write(p,{'v':1});self.assertEqual(r.read(p),{'v':1})
    def test_checkpoint_readback(self):
        p=self.root/'x.gz';r.save_cache(p,'fp',{'v':[1,2]});self.assertEqual(r.load_cache(p,'fp'),{'v':[1,2]})
    def test_existing_checkpoint_not_overwritten(self):
        p=self.root/'x.gz';r.save_cache(p,'fp',{'v':1})
        with self.assertRaises(ValueError):r.save_cache(p,'fp',{'v':2})
    def test_cache_lineage_rejected(self):
        p=self.root/'x.gz';r.save_cache(p,'fp',{'v':1})
        with self.assertRaises(ValueError):r.load_cache(p,'different')
    def test_corrupt_cache_rejected(self):
        p=self.root/'x.gz';r.save_cache(p,'fp',{'v':1});x=json.loads(gzip.decompress(p.read_bytes()));x['payload']['v']=2
        p.write_bytes(gzip.compress(json.dumps(x).encode()))
        with self.assertRaises(ValueError):r.load_cache(p,'fp')
    def test_missing_cache_is_not_a_hit(self):self.assertIsNone(r.load_cache(self.root/'absent','fp'))
    def test_path_escape_rejected(self):
        with self.assertRaises(ValueError):r.inside(self.root,'../secrets')
    def test_symlink_escape_rejected(self):
        p=self.root/'escape';p.symlink_to('/tmp')
        with self.assertRaises(ValueError):r.inside(self.root,'escape/x')
    def test_code_hash_ignores_outputs(self):
        (self.root/'a.py').write_text('x=1');before=r.code_hash(self.root)
        (self.root/'outputs').mkdir();(self.root/'outputs/a.py').write_text('x=2')
        self.assertEqual(r.code_hash(self.root),before)
    def test_code_hash_detects_source_change(self):
        p=self.root/'a.py';p.write_text('x=1');before=r.code_hash(self.root);p.write_text('x=2')
        self.assertNotEqual(r.code_hash(self.root),before)
    def test_test_double_mechanics_distinguishes_early_and_final_effect(self):
        with patch.object(r,'OUT',self.root):rows=r.mechanics(GAME,transition)
        self.assertEqual([x['terminal_cash_delta'] for x in rows],[0,2])
    def build_branches(self):
        pairs=[];branches=[];inventory=[]
        groups=[(1601,0,'coordinated'),(1601,0,'sequential'),(1601,1,'coordinated'),(1601,1,'sequential'),
                (1602,0,'coordinated'),(1602,0,'sequential'),(1602,1,'sequential')]
        for seed,seat,arm in groups:
            payload,key=make_payload(seat,arm,718,seed)
            items=[rollout(payload,key,variant,GAME,transition,assert_source_transition,lambda *x:None,
                           actor_factory=factory(718),context_extractor=extract) for variant in ('control','aligned')]
            row=pair_results(*items);row['episode_id']=r.digest(key)[:20]
            pairs.append(row);branches.extend(items);inventory.append(key)
        return pairs,branches,inventory
    def test_end_to_end_seven_synthetic_pairs_exports(self):
        pairs,branches,inv=self.build_branches()
        with patch.object(r,'OUT',self.root):
            report=r.summarize(pairs,branches,inv,{'tests':0},{},'test-double',0)
        self.assertEqual(report['completed_pairs'],7);self.assertEqual(report['primary_pairs'],3)
        self.assertEqual(report['negative_control_pairs'],4);self.assertEqual(report['total_causal_descriptors'],170)
        self.assertEqual(report['new_suffix_interpreter_calls'],322)
        self.assertFalse(report['official_metric_effect_measured']);self.assertFalse(report['new_context_candidates_used_to_change_actions'])
    def test_synthetic_plotly_figures(self):
        from visualize_continuation import figures,export_dashboard
        pairs,branches,inv=self.build_branches()
        with patch.object(r,'OUT',self.root):
            report=r.summarize(pairs,branches,inv,{}, {},'test-double',0)
        charts=figures(self.root,r.BASE/'reference');self.assertEqual(len(charts),7)
        for f in charts:self.assertTrue(f.to_json())
        export_dashboard(charts,self.root/'synthetic.html',report['decision'],'SYNTHETIC TEST DOUBLES')
        self.assertIn('SYNTHETIC TEST DOUBLES',(self.root/'synthetic.html').read_text())
    def test_report_counts_reused_branches_separately(self):
        pairs,branches,inv=self.build_branches()
        for b in branches:b['reused_from_checkpoint']=True
        with patch.object(r,'OUT',self.root):report=r.summarize(pairs,branches,inv,{}, {},'test-double',0)
        self.assertEqual(report['new_suffix_interpreter_calls'],0);self.assertEqual(report['represented_suffix_interpreter_calls'],322)
