import unittest,tempfile,json,gzip,shutil
from pathlib import Path
from copy import deepcopy
from artifact_io import *
from review_inputs import action_stream,checkpoint
from run_diagnosis import decomposition
BASE=Path(__file__).resolve().parents[1]
class EvidenceTests(unittest.TestCase):
    def test_real_action_binding(self):
        s=action_stream(BASE/'reference/notebook12',read(BASE/'reference/input_hashes.json'))
        self.assertEqual(len(s['control']['actions']),239);self.assertEqual(len(s['defer']['actions']),239)
    def test_real_negative_endpoint(self):
        s=action_stream(BASE/'reference/notebook12');self.assertEqual(s['defer']['checkpoint']['metrics']['coins']-s['control']['checkpoint']['metrics']['coins'],-396)
    def test_refuse_changed_hash(self):
        h=read(BASE/'reference/input_hashes.json');h[next(iter(h))]='0'*64
        with self.assertRaises(ValueError):action_stream(BASE/'reference/notebook12',h)
    def test_refuse_missing_action(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'prior';shutil.copytree(BASE/'reference/notebook12',root)
            p=root/'outputs/callback_trace.jsonl';lines=p.read_text().splitlines();p.write_text('\n'.join(lines[:-1]))
            with self.assertRaises(ValueError):action_stream(root)
    def test_refuse_wrong_role(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'prior';shutil.copytree(BASE/'reference/notebook12',root)
            p=root/'outputs/callback_trace.jsonl';txt=p.read_text();p.write_text(txt.replace('"role": "opponent"','"role": "candidate"',1))
            with self.assertRaises(ValueError):action_stream(root)
    def test_checkpoint_readback(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.gz';save_cache(p,'x',{'value':[1,2]});self.assertEqual(load_cache(p,'x'),{'value':[1,2]})
    def test_checkpoint_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.gz';save_cache(p,'x',{})
            with self.assertRaises(ValueError):save_cache(p,'x',{})
    def test_checkpoint_bad_fingerprint(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.gz';save_cache(p,'x',{})
            with self.assertRaises(ValueError):load_cache(p,'y')
    def test_checkpoint_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.gz';save_cache(p,'x',{});j=json.loads(gzip.decompress(p.read_bytes()));j['payload']={'changed':True};p.write_bytes(gzip.compress(json.dumps(j).encode()))
            with self.assertRaises(ValueError):load_cache(p,'x')
    def test_safe_paths(self):
        with self.assertRaises(ValueError):inside(BASE,'../../escape')
    def test_decomposition_exact(self):
        b=[{'mode':'control','trades':[{'player':0,'operation':'SELL','item':'WHEAT','cash':100,'units':5}]},{'mode':'defer','trades':[{'player':0,'operation':'SELL','item':'WHEAT','cash':132,'units':6}]}]
        r=decomposition(b)[0];self.assertEqual(r['cash_delta'],32);self.assertAlmostEqual(r['quantity_component']+r['average_price_component'],32)
    def test_zero_sales_missing_price(self):
        b=[{'mode':'control','trades':[]},{'mode':'defer','trades':[{'player':0,'operation':'SELL','item':'WHEAT','cash':5,'units':1}]}]
        r=decomposition(b)[0];self.assertIsNone(r['quantity_component']);self.assertEqual(r['cash_delta'],5)
    def test_spending_sign(self):
        b=[{'mode':'control','trades':[{'player':0,'operation':'BUY_SEED','item':'WHEAT','cash':-20,'units':2}]},{'mode':'defer','trades':[]}];self.assertEqual(decomposition(b)[0]['cash_delta'],20)
