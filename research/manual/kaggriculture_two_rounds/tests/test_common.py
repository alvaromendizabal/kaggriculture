import unittest,tempfile,ast,json,gzip,subprocess,sys,time
from pathlib import Path
from unittest.mock import patch
from copy import deepcopy
from io_utils import *
from feature_common import clock,integer,distance
from policies import transform
from experiment import run_game,compare,measure
from tests.fixtures import obs,SOURCE,GAME,ToyEnv,toy_factory,pass_action
class SharedTests(unittest.TestCase):
    def test_clock_none(self):o=obs();o['step']=None;self.assertEqual(clock(o),244)
    def test_clock_conflict(self):o=obs();o['step']=9;self.assertRaises(ValueError,clock,o)
    def test_clock_end(self):self.assertEqual(clock(obs(day=29,hour=22)),718)
    def test_clock_terminal_reject(self):self.assertRaises(ValueError,clock,obs(day=29,hour=23))
    def test_noninteger(self):self.assertRaises(ValueError,integer,1.1)
    def test_bool_reject(self):self.assertRaises(ValueError,integer,True)
    def test_nan(self):self.assertRaises(ValueError,integer,float('nan'))
    def test_board_distance(self):self.assertEqual(distance((0,0),(9,9)),18)
    def test_out_of_board(self):self.assertRaises(ValueError,distance,(10,0),(0,0))
    def test_source_substitution(self):self.assertEqual(ast.unparse(transform(SOURCE)).count('__harvest_value('),1)
    def test_water_unchanged(self):self.assertIn("not tile['watered_today']",ast.unparse(transform(SOURCE)))
    def test_wrong_source(self):self.assertRaises(ValueError,transform,'def f(): return 2')
    def test_twice_source(self):self.assertRaises(ValueError,transform,SOURCE+'\n'+SOURCE.replace('__call__','other'))
    def test_atomic(self):
        with tempfile.TemporaryDirectory() as td:p=Path(td)/'x';atomic(p,b'a');atomic(p,b'b');self.assertEqual(p.read_bytes(),b'b')
    def test_cache(self):
        with tempfile.TemporaryDirectory() as td:p=Path(td)/'x.gz';save(p,'fp',{'x':4});self.assertEqual(load(p,'fp'),{'x':4})
    def test_cache_lineage(self):
        with tempfile.TemporaryDirectory() as td:p=Path(td)/'x.gz';save(p,'fp',{});self.assertRaises(ValueError,load,p,'bad')
    def test_cache_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:p=Path(td)/'x.gz';save(p,'fp',{});self.assertRaises(ValueError,save,p,'fp',{})
    def test_cache_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.gz';save(p,'fp',{});v=json.loads(gzip.decompress(p.read_bytes()));v['payload']={'bad':1};p.write_bytes(gzip.compress(canonical(v)));self.assertRaises(ValueError,load,p,'fp')
    def test_path_escape(self):self.assertRaises(ValueError,inside,Path('/tmp/a'),'../b')
    def test_digest_nonfinite(self):self.assertRaises(ValueError,digest,{'a':float('nan')})
    def test_observation_mutation_rejected(self):
        def actor(o):o['day']=4;return pass_action(o)
        self.assertRaises(ValueError,measure,actor,obs(),'test',lambda *a:None)
    def test_callback_latency_gate(self):
        with patch('experiment.time.perf_counter',side_effect=[0,1]):self.assertRaises(RuntimeError,measure,pass_action,obs(),'x',lambda *a:None)
    def test_driver_complete_control(self):
        b=run_game(GAME,lambda s:ToyEnv(),'17','control',{'id':'b','seed':77,'seat':0,'opponent':'crop_full'},lambda *a:None,lambda *a,**k:None,toy_factory)
        self.assertEqual((b['transitions'],b['null_checks'],b['action_changes']),(719,719,0))
    def test_driver_candidate_pair(self):
        kw=(GAME,lambda s:ToyEnv(),'18');blk={'id':'b','seed':77,'seat':1,'opponent':'crop_full'}
        c=run_game(*kw,'control',blk,lambda *a:None,lambda *a,**k:None,toy_factory);a=run_game(*kw,'candidate',blk,lambda *a:None,lambda *a,**k:None,toy_factory)
        r=compare(c,a);self.assertEqual(r['coins_delta'],1);self.assertEqual(r['action_changes'],1)
    def test_supervisor_termination(self):
        from run_research import kill_group
        p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'],start_new_session=True);kill_group(p);self.assertIsNotNone(p.poll())
    def test_independent_round_sources(self):
        import arrival_features,headroom_features
        self.assertEqual(len(arrival_features.FIELDS),len(headroom_features.FIELDS));self.assertEqual(len(arrival_features.SUMMARY),len(headroom_features.SUMMARY))

class RunnerTests(unittest.TestCase):
    def test_shared_control_is_reused(self):
        import run_research as runner
        import experiment
        real=experiment.run_game;protocol=read(Path(runner.BASE)/'PROTOCOL.json');calls=[]
        def artificial(game,maker,rid,mode,block,emit,log):
            calls.append((rid,mode));return real(GAME,lambda s:ToyEnv(),rid,mode,block,lambda *a:None,lambda *a,**k:None,toy_factory)
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);write(base/'PROTOCOL.json',protocol)
            with patch.object(runner,'BASE',base),patch.object(runner,'OUT',base/'outputs'),patch.object(runner,'preflight',return_value=(__import__('types').SimpleNamespace(game=GAME,make_environment=lambda s:ToyEnv()),None,None,'fp')),patch.object(runner,'verify_stage',return_value={'fingerprint':'fp','decision':'FRESH_BLOCKS_ALLOWED'}),patch('experiment.run_game',side_effect=artificial),patch.object(runner,'log'),patch.object(runner,'emit'):
                runner.pair('17',1,base);runner.pair('18',1,base)
                self.assertEqual(calls,[('17','control'),('17','candidate'),('18','candidate')])
                self.assertEqual(read(base/'outputs/round18/pair1/report.json')['new_games'],1)
    def test_nonactivation_starts_no_games(self):
        import run_research as runner
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            with patch.object(runner,'BASE',base),patch.object(runner,'OUT',base/'outputs'),patch.object(runner,'preflight',return_value=(__import__('types').SimpleNamespace(game=GAME,make_environment=lambda s:ToyEnv()),None,None,'fp')),patch.object(runner,'verify_stage',return_value={'fingerprint':'fp','decision':'STOP_NO_ACTION_ACTIVATION'}),patch('experiment.run_game') as run,patch.object(runner,'log'):
                runner.pair('17',1,base);run.assert_not_called()
                self.assertEqual(read(base/'outputs/round17/pair1/report.json')['new_games'],0)
    def test_negative_pair_blocks_next(self):
        import run_research as runner
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            def verify(r,s):return {'fingerprint':'fp','decision':'FRESH_BLOCKS_ALLOWED' if s=='screen' else 'STOP_NEGATIVE_ENDPOINT'}
            with patch.object(runner,'BASE',base),patch.object(runner,'OUT',base/'outputs'),patch.object(runner,'preflight',return_value=(__import__('types').SimpleNamespace(game=GAME,make_environment=lambda s:ToyEnv()),None,None,'fp')),patch.object(runner,'verify_stage',side_effect=verify),patch('experiment.run_game') as run,patch.object(runner,'log'):
                runner.pair('18',2,base);run.assert_not_called();self.assertEqual(read(base/'outputs/round18/pair2/report.json')['decision'],'SKIPPED_PREVIOUS_STOP')
    def test_failed_stage_not_retried(self):
        import run_research as runner
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);write(out/'round17/screen/status.json',{'status':'FAILED'})
            with patch.object(runner,'OUT',out),patch('run_research.subprocess.Popen') as spawn:
                self.assertRaises(RuntimeError,runner.supervise,'17','screen',out);spawn.assert_not_called()
    def test_real_supervisor_deadline(self):
        import run_research as runner
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);(base/'run_research.py').write_text('import time;time.sleep(10)')
            with patch.object(runner,'BASE',base),patch.object(runner,'OUT',base/'outputs'),patch('run_research.time.monotonic',side_effect=[0,121]):
                self.assertRaises(TimeoutError,runner.supervise,'17','screen',base)
            self.assertEqual(read(base/'outputs/round17/screen/status.json')['status'],'FAILED')
            self.assertFalse((base/'outputs/.execution.lock').exists())
    def test_bundle_after_failure(self):
        import run_research as runner
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);write(base/'outputs/round17/failure.json',{'message':'test'})
            with patch.object(runner,'BASE',base),patch.object(runner,'OUT',base/'outputs'):runner.bundle()
            import zipfile,hashlib
            with zipfile.ZipFile(base/'kaggriculture_two_rounds_results.zip') as z:
                mf=json.loads(z.read('BUNDLE_MANIFEST.json'))
                for n,h in mf['files'].items():self.assertEqual(hashlib.sha256(z.read(n)).hexdigest(),h)
