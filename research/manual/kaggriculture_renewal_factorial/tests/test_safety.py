from pathlib import Path
from unittest.mock import patch
import tempfile, unittest, json, subprocess
import run_factorial as runner
from factorial_io import write,sha,code_hash

class SafetyTests(unittest.TestCase):
    def test_failed_stage_never_relaunches(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'outputs';write(out/'screen/status.json',{'status':'FAILED'})
            with patch.object(runner,'OUT',out), patch.object(runner.subprocess,'Popen') as launch:
                with self.assertRaises(RuntimeError):runner.supervise('screen',Path(d))
                launch.assert_not_called()
    def test_active_stage_never_relaunches(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'outputs';write(out/'pilot/status.json',{'status':'RUNNING'})
            with patch.object(runner,'OUT',out), patch.object(runner.subprocess,'Popen') as launch:
                with self.assertRaises(RuntimeError):runner.supervise('pilot',Path(d))
                launch.assert_not_called()
    def test_verified_stage_reuse_has_no_child(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'outputs';write(out/'screen/status.json',{'status':'COMPLETED'})
            with patch.object(runner,'OUT',out), patch.object(runner,'verify_stage',return_value={'fingerprint':'abc'}), patch.object(runner,'preflight',return_value=(None,None,None,'abc',None)),patch.object(runner.subprocess,'Popen') as launch:
                runner.supervise('screen',Path(d));launch.assert_not_called()
    def test_reuse_refuses_new_fingerprint(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'outputs';write(out/'screen/status.json',{'status':'COMPLETED'})
            with patch.object(runner,'OUT',out), patch.object(runner,'verify_stage',return_value={'fingerprint':'old'}), patch.object(runner,'preflight',return_value=(None,None,None,'new',None)):
                with self.assertRaises(ValueError):runner.supervise('screen',Path(d))
    def test_completed_report_hash_checked(self):
        with tempfile.TemporaryDirectory() as d:
            b=Path(d);out=b/'outputs';write(out/'pilot/report.json',{'code_sha256':code_hash(b),'output_sha256':{}})
            write(out/'pilot/status.json',{'status':'COMPLETED','report_sha256':'wrong'})
            with patch.object(runner,'BASE',b),patch.object(runner,'OUT',out):
                with self.assertRaises(ValueError):runner.verify_stage('pilot')
    def test_output_checksum_checked(self):
        with tempfile.TemporaryDirectory() as d:
            b=Path(d);out=b/'outputs';write(out/'table.json',{'value':1})
            write(out/'pilot/report.json',{'code_sha256':code_hash(b),'output_sha256':{'table.json':'wrong'}})
            write(out/'pilot/status.json',{'status':'COMPLETED','report_sha256':sha(out/'pilot/report.json')})
            with patch.object(runner,'BASE',b),patch.object(runner,'OUT',out):
                with self.assertRaises(ValueError):runner.verify_stage('pilot')
    def test_real_budget_terminates_sleeping_child(self):
        with tempfile.TemporaryDirectory() as d:
            b=Path(d);out=b/'outputs';(b/'run_factorial.py').write_text('import time\ntime.sleep(10)\n')
            launched=[];real=subprocess.Popen
            def spy(*args,**kwargs):
                p=real(*args,**kwargs);launched.append(p);return p
            with patch.object(runner,'BASE',b),patch.object(runner,'OUT',out),patch.dict(runner.CAPS,{'screen':.01}),patch.object(runner.subprocess,'Popen',side_effect=spy):
                with self.assertRaises(TimeoutError):runner.supervise('screen',b)
            self.assertEqual(len(launched),1);self.assertIsNotNone(launched[0].poll())
            self.assertEqual(json.loads((out/'screen/status.json').read_text())['status'],'FAILED')
    def test_bundle_excludes_output_symlink(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            b=Path(d);out=b/'outputs';out.mkdir();secret=b/'secret.txt';secret.write_text('do not export')
            (out/'secret.txt').symlink_to(secret);write(out/'failure.json',{'error':'test'})
            with patch.object(runner,'BASE',b),patch.object(runner,'OUT',out):runner.bundle()
            with zipfile.ZipFile(b/'kaggriculture_renewal_factorial_results.zip') as z:
                self.assertNotIn('outputs/secret.txt',z.namelist());self.assertIn('outputs/failure.json',z.namelist())
