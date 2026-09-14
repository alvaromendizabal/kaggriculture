import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tempfile,unittest,json,gzip
from copy import deepcopy
from evidence import inside,load_branch,read,digest,diagnose
from run_timing import save_cache,load_cache,choose_decision,write,code_hash
BASE=Path(__file__).resolve().parents[1]
class TestRunner(unittest.TestCase):
    def test_path_guard(self):
        with self.assertRaises(ValueError):inside(BASE,'../escape')
    def test_atomic_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';write(p,{'yes':1});self.assertEqual(read(p),{'yes':1})
    def test_cache_readback(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.gz';save_cache(p,'abc',{'ok':1});self.assertEqual(load_cache(p,'abc'),{'ok':1})
    def test_cache_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.gz';save_cache(p,'abc',{})
            with self.assertRaises(ValueError):save_cache(p,'abc',{})
    def test_cache_lineage(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.gz';save_cache(p,'abc',{})
            with self.assertRaises(ValueError):load_cache(p,'def')
    def test_cache_corrupt(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.gz';save_cache(p,'abc',{'ok':1});x=json.loads(gzip.decompress(p.read_bytes()));x['payload']['ok']=2;p.write_bytes(gzip.compress(json.dumps(x).encode()))
            with self.assertRaises(ValueError):load_cache(p,'abc')
    def test_missing_cache(self):self.assertIsNone(load_cache(BASE/'missing.gz','abc'))
    def row(self,delta=0,changed=True):return {'role':'primary','coins_delta':delta,'coin_margin_delta':delta,'local_match_score_delta':0,'final_market_changed':changed}
    def test_stop_loss(self):self.assertEqual(choose_decision([self.row(-3)],False),'STOP_NEGATIVE_FINAL_EFFECT')
    def test_stop_null(self):self.assertEqual(choose_decision([self.row()],True),'STOP_NO_FINAL_BENEFIT')
    def test_stop_nonactivation(self):self.assertEqual(choose_decision([self.row(changed=False)],True),'STOP_NO_ACTIVATION')
    def test_stop_incomplete(self):self.assertEqual(choose_decision([self.row(1)],False),'INCOMPLETE_NO_GENERALIZATION_CLAIM')
    def test_promising_not_winner(self):self.assertEqual(choose_decision([self.row(1)],True),'PROMISING_DEVELOPMENT_ONLY_FRESH_VALIDATION_REQUIRED')
    def test_margin_loss_gate(self):
        r=self.row(5);r['coin_margin_delta']=-1;self.assertEqual(choose_decision([r],True),'STOP_NEGATIVE_FINAL_EFFECT')
    def test_negative_controls_not_efficacy(self):
        r=self.row(5);r['role']='negative_control';self.assertEqual(choose_decision([r],True),'STOP_NO_ACTIVATION')
    def branches(self):
        d=BASE/'reference'
        return [load_branch(d/f'nb09_{v}.json.gz') for v in ('control','aligned')]
    def test_real_returned_diagnosis(self):
        d=diagnose(*self.branches());self.assertEqual(d['cash_delta'],-3.)
        self.assertEqual([r for r in d['product_deltas'] if r['delta']!=0],[{'product':'TOMATO','control':335.,'aligned':332.,'delta':-3.}])
    def test_refuses_fake_pair(self):
        c,a=self.branches();a['key']['seed']=20
        with self.assertRaises(ValueError):diagnose(c,a)
    def test_refuses_changed_opponent(self):
        c,a=self.branches();a['opponent_actions'][0]['market']=[['HIRE']]
        with self.assertRaises(ValueError):diagnose(c,a)
    def test_refuses_unreconciled_income(self):
        c,a=self.branches();a['trace'][20]['own_cash_after']+=1
        with self.assertRaises(ValueError):diagnose(c,a)
    def test_refuses_interfering_trade(self):
        c,a=self.branches()
        for x in (c,a):x['opponent_actions'][20]['market']=[['SELL','TOMATO',3]]
        with self.assertRaises(ValueError):diagnose(c,a)
    def test_branch_checksum(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.gz';x={'fingerprint':'a','payload':{'ok':1}};x['checksum']='wrong';p.write_bytes(gzip.compress(json.dumps(x).encode()))
            with self.assertRaises(ValueError):load_branch(p)
    def test_code_hash_ignores_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'main.py').write_text('pass');a=code_hash(p);(p/'outputs').mkdir();(p/'outputs/x.py').write_text('new');self.assertEqual(a,code_hash(p))
