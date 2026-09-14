import ast,gzip,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from copy import deepcopy
from io_utils import atomic,canonical,digest,inside,load,save,sha,write,read
from feature_common import clock,distance,validate
from policies import transform
from experiment import compare
from tests.fixtures import observation

TEMPLATE='''def score(obs, farm, private, index, position, job, travel):
    return job.priority / (1 + travel)
'''
class CommonTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.p=self.root/'x.gz'
 def tearDown(self):self.tmp.cleanup()
 def test_01_canonical_key_order(self):self.assertEqual(digest({'a':1,'b':2}),digest({'b':2,'a':1}))
 def test_02_nonfinite_rejected(self):
  with self.assertRaises(ValueError):canonical({'a':float('nan')})
 def test_03_atomic_roundtrip(self):atomic(self.root/'a/b.txt',b'abc');self.assertEqual((self.root/'a/b.txt').read_bytes(),b'abc')
 def test_04_checkpoint_roundtrip(self):save(self.p,'f',{'x':1});self.assertEqual(load(self.p,'f'),{'x':1})
 def test_05_checkpoint_no_overwrite(self):
  save(self.p,'f',{'x':1})
  with self.assertRaises(ValueError):save(self.p,'f',{'x':2})
 def test_06_wrong_fingerprint(self):
  save(self.p,'f',{'x':1})
  with self.assertRaises(ValueError):load(self.p,'g')
 def test_07_tampered_checksum(self):
  save(self.p,'f',{'x':1});d=json.loads(gzip.decompress(self.p.read_bytes()));d['payload']['x']=2;self.p.write_bytes(gzip.compress(canonical(d)))
  with self.assertRaises(ValueError):load(self.p,'f')
 def test_08_missing_is_none(self):self.assertIsNone(load(self.p,'f'))
 def test_09_checkpoints_deterministic(self):save(self.p,'f',{});q=self.root/'q.gz';save(q,'f',{});self.assertEqual(self.p.read_bytes(),q.read_bytes())
 def test_10_json_roundtrip(self):q=self.root/'q.json';write(q,{'a':1});self.assertEqual(read(q),{'a':1})
 def test_11_escape_refused(self):
  with self.assertRaises(ValueError):inside(self.root,'../../escape')
 def test_12_symlink_escape_refused(self):
  (self.root/'link').symlink_to('/tmp',target_is_directory=True)
  with self.assertRaises(ValueError):inside(self.root,'link/escaped')
 def test_13_inside_allowed(self):self.assertEqual(inside(self.root,'sub/a'),self.root/'sub/a')
 def test_14_clock_terminal(self):self.assertEqual(clock(observation(hour=22,day=29)),718)
 def test_15_clock_conflict(self):
  o=observation();o['step']=1
  with self.assertRaises(ValueError):clock(o)
 def test_16_clock_hour_invalid(self):
  with self.assertRaises(ValueError):clock(observation(hour=24))
 def test_17_clock_missing_derived(self):o=observation();del o['step'];self.assertEqual(clock(o),252)
 def test_18_distance_geometry(self):self.assertEqual(distance((0,0),(9,9)),18)
 def test_19_distance_symmetry(self):self.assertEqual(distance((2,3),(6,4)),distance((6,4),(2,3)))
 def test_20_distance_bounds(self):
  with self.assertRaises(ValueError):distance((10,0),(0,0))
 def test_21_board_shape(self):
  o=observation();o['farms'][0]['tiles'].pop()
  with self.assertRaises(ValueError):validate(o)
 def test_22_one_rewrite(self):self.assertEqual(ast.unparse(transform(TEMPLATE)).count('__service_score'),1)
 def test_23_missing_rewrite_refused(self):
  with self.assertRaises(ValueError):transform('def f(): return 1')
 def test_24_multiple_rewrites_refused(self):
  with self.assertRaises(ValueError):transform(TEMPLATE+'\n'+TEMPLATE.replace('def score','def other'))
 def test_25_no_source_mutation(self):b=TEMPLATE;transform(TEMPLATE);self.assertEqual(b,TEMPLATE)
 def test_26_null_hook_equivalence(self):
  ns={'__service_score':lambda obs,f,p,i,pos,j,t:j.priority/(1+t)};exec(compile(transform(TEMPLATE),'<test>','exec'),ns)
  from tests.fixtures import job
  self.assertEqual(ns['score'](None,None,None,0,None,job(),8),100/9)
 def test_27_only_priority_formula_changed(self):
  changed=ast.unparse(transform(TEMPLATE));self.assertIn('return __service_score',changed);self.assertNotIn('WATER',changed)
 def branch(self):return {'block':{'id':'b1','seed':1,'seat':0,'opponent':'test'},'initial_sha256':'a','transitions':719,'null_checks':719,'action_changes':3,'metrics':{'coins':10,'opponent_coins':9,'coin_margin':1,'local_match_score':1,'residual_product_units':0}}
 def test_28_comparison_identity(self):a=self.branch();self.assertEqual(compare(a,deepcopy(a))['coins_delta'],0)
 def test_29_negative_cash_guard(self):
  a=self.branch();b=deepcopy(a);b['metrics']['coins']=9;b['metrics']['coin_margin']=0;b['metrics']['local_match_score']=.5
  self.assertEqual(compare(a,b)['decision'],'STOP_NEGATIVE_ENDPOINT')
 def test_30_mismatched_initial_refused(self):
  a=self.branch();b=deepcopy(a);b['initial_sha256']='b'
  with self.assertRaises(ValueError):compare(a,b)
 def test_31_incomplete_pair_refused(self):
  a=self.branch();b=deepcopy(a);b['transitions']=718
  with self.assertRaises(ValueError):compare(a,b)
 def test_32_completed_checkpoint_survives_interruption(self):
  # Deliberate tiny interruption: reuse only completed work, not an unfinished game.
  save(self.p,'f',{'completed':True});before=sha(self.p)
  child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])
  try:child.terminate();child.wait(timeout=2)
  finally:
   if child.poll() is None:child.kill();child.wait()
  self.assertEqual(sha(self.p),before);self.assertTrue(load(self.p,'f')['completed'])
