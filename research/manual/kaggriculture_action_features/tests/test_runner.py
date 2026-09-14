import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run_next as r

class Checkpoints(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.json.gz';r.save_cache(p,'fingerprint',{'state':1})
            self.assertEqual(r.load_cache(p,'fingerprint'),{'state':1})
    def test_missing_is_miss(self):
        with tempfile.TemporaryDirectory() as t:self.assertIsNone(r.load_cache(Path(t)/'missing','f'))
    def test_fingerprint_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.json.gz';r.save_cache(p,'a',{'v':1})
            with self.assertRaisesRegex(ValueError,'Different'):r.load_cache(p,'b')
    def test_corruption_fails(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.json.gz';p.write_bytes(b'not gzip')
            with self.assertRaises(Exception):r.load_cache(p,'b')
    def test_checksum_mismatch_fails(self):
        import gzip,json
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.json.gz';r.save_cache(p,'a',{'v':1})
            x=json.loads(gzip.decompress(p.read_bytes()));x['payload']['v']=2
            p.write_bytes(gzip.compress(json.dumps(x).encode()))
            with self.assertRaisesRegex(ValueError,'checksum'):r.load_cache(p,'a')
    def test_atomic_write_creates_parent(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'sub/a.json';r.write(p,{'v':1});self.assertEqual(r.read(p),{'v':1})
    def test_path_traversal(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):r.contained(t,'../x')
    def test_absolute_escape(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):r.contained(t,'/etc/passwd')
    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'link';p.symlink_to('/etc')
            with self.assertRaises(ValueError):r.contained(t,'link/passwd')
    def test_safe_relative(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(r.contained(t,'a'),Path(t)/'a')
    def test_prerequisite_never_run(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(r.prior_state(Path(t)),'never_run')
    def test_prerequisite_pass_found(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);r.write(p/'outputs/run_status.json',{'status':'PASSED'})
            self.assertEqual(r.prior_state(p),'passed')
    def test_prerequisite_failed_no_retry(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);r.write(p/'outputs/run_status.json',{'status':'FAILED'})
            with self.assertRaisesRegex(RuntimeError,'do not retry'):r.prior_state(p)
    def test_prerequisite_unfinished_report(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);r.write(p/'outputs/report.json',{'status':'PASSED'})
            with self.assertRaisesRegex(RuntimeError,'incomplete'):r.prior_state(p)
    def test_prerequisite_cache_without_status(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);r.write(p/'outputs/checkpoints/episode.json',{})
            with self.assertRaises(RuntimeError):r.prior_state(p)
    def test_ensure_reuses_success_without_compute(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);previous=root/'previous';r.write(previous/'outputs/report.json',{'x':1})
            args=SimpleNamespace(previous=previous,resume=root/'resume')
            with patch.object(r,'OUT',root/'out'),patch.object(r,'validate_previous_code'),patch.object(r,'prior_state',return_value='passed'),patch.object(r,'verify_previous',return_value={'source_commit':r.COMMIT,'saved_observations':161}),patch.object(r,'supervise') as run,contextlib.redirect_stdout(io.StringIO()):
                r.ensure06(args);run.assert_not_called()
                self.assertTrue(r.read(root/'out/prerequisite.json')['reused_existing_pass'])
    def test_ensure_runs_never_attempted_once(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);previous=root/'previous';r.write(previous/'outputs/report.json',{'x':1})
            args=SimpleNamespace(previous=previous,resume=root/'resume')
            with patch.object(r,'OUT',root/'out'),patch.object(r,'validate_previous_code'),patch.object(r,'prior_state',return_value='never_run'),patch.object(r,'runtime_executable',return_value=Path('/verified/python')),patch.object(r,'verify_previous',return_value={'source_commit':r.COMMIT,'saved_observations':161}),patch.object(r,'supervise') as run,contextlib.redirect_stdout(io.StringIO()):
                r.ensure06(args);run.assert_called_once()
                self.assertEqual(run.call_args.args[1],195)
                self.assertFalse(r.read(root/'out/prerequisite.json')['reused_existing_pass'])
    def test_ensure_does_not_retry_failure(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);args=SimpleNamespace(previous=root,resume=root)
            with patch.object(r,'validate_previous_code'),patch.object(r,'prior_state',side_effect=RuntimeError('prior failure')),patch.object(r,'supervise') as run:
                with self.assertRaises(RuntimeError):r.ensure06(args)
                run.assert_not_called()
    def test_synthetic_report_not_a_live_pass(self):
        with tempfile.TemporaryDirectory() as t,patch.object(r,'OUT',Path(t)):
            r.write(Path(t)/'report.json',{'status':'SYNTHETIC_DEMO_ONLY','code_sha256':r.code_hash()})
            r.write(Path(t)/'run_status.json',{'status':'PASSED'})
            with self.assertRaisesRegex(ValueError,'Report status'):r.verify()
    def test_child_nonzero_stops(self):
        import sys
        with tempfile.TemporaryDirectory() as t,patch.object(r,'OUT',Path(t)),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError):r.supervise([sys.executable,'-c','raise SystemExit(4)'],2,Path(t),'TEST')
    def test_hard_budget_terminates(self):
        import sys,time
        with tempfile.TemporaryDirectory() as t,patch.object(r,'OUT',Path(t)),contextlib.redirect_stdout(io.StringIO()):
            tick=time.monotonic()
            with self.assertRaises(TimeoutError):r.supervise([sys.executable,'-c','import time; time.sleep(30)'],0.15,Path(t),'TEST')
            self.assertLess(time.monotonic()-tick,3)

if __name__=='__main__':unittest.main()
