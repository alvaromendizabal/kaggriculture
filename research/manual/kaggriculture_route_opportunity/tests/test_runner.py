import tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import run_routes as runner
from route_io import write,sha,code_hash

class RunnerTests(unittest.TestCase):
    def setUp(self):self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);self.out=self.root/'outputs'
    def tearDown(self):self.t.cleanup()
    def test_prior_failure_never_restarted(self):
        write(self.out/'screen/status.json',{'status':'FAILED'})
        with patch.object(runner,'OUT',self.out):
            with self.assertRaises(RuntimeError):runner.supervise('screen',self.root)
    def test_prior_running_never_duplicated(self):
        write(self.out/'screen/status.json',{'status':'RUNNING'})
        with patch.object(runner,'OUT',self.out):
            with self.assertRaises(RuntimeError):runner.supervise('screen',self.root)
    def test_verified_completion_reused(self):
        report={'decision':'STOP_NO_ACTION_ACTIVATION','code_sha256':code_hash(self.root),'output_sha256':{}}
        write(self.out/'screen/report.json',report)
        write(self.out/'screen/status.json',{'status':'COMPLETED','report_sha256':sha(self.out/'screen/report.json')})
        with patch.object(runner,'OUT',self.out),patch.object(runner,'BASE',self.root),patch.object(runner,'prior_check'):
            runner.supervise('screen',self.root)
    def test_bad_report_hash_not_reused(self):
        write(self.out/'screen/report.json',{'code_sha256':'x'})
        write(self.out/'screen/status.json',{'status':'COMPLETED','report_sha256':'bad'})
        with patch.object(runner,'OUT',self.out):
            with self.assertRaises(ValueError):runner.verify_stage('screen')
    def test_failure_bundle(self):
        write(self.out/'failure_screen.json',{'error':'diagnostic'})
        (self.out/'private.env').write_text('secret')
        with patch.object(runner,'OUT',self.out),patch.object(runner,'BASE',self.root):runner.bundle()
        with zipfile.ZipFile(self.root/'kaggriculture_route_opportunity_results.zip') as z:
            self.assertIn('outputs/failure_screen.json',z.namelist());self.assertNotIn('outputs/private.env',z.namelist())
    def test_no_symlink_bundling(self):
        self.out.mkdir();(self.root/'outside.json').write_text('private');(self.out/'link.json').symlink_to(self.root/'outside.json')
        with patch.object(runner,'OUT',self.out),patch.object(runner,'BASE',self.root):runner.bundle()
        with zipfile.ZipFile(self.root/'kaggriculture_route_opportunity_results.zip') as z:self.assertNotIn('outputs/link.json',z.namelist())
