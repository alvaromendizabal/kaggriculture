import gzip,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from research_io import *
BASE=Path(__file__).resolve().parents[1]
class IntegrityTests(unittest.TestCase):
    def test_actual_prior_result(self):
        r=read(BASE/'reference/notebook14_screen_report.json');self.assertEqual((r['action_changes'],r['observations']),(0,156))
    def test_prior_no_pilot_score(self):self.assertEqual(read(BASE/'reference/notebook14_pilot_report.json')['completed_pairs'],0)
    def test_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cp.gz';save_cache(p,'f',{'a':4});self.assertEqual(load_cache(p,'f'),{'a':4})
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cp.gz';save_cache(p,'f',{'a':4})
            with self.assertRaises(ValueError):save_cache(p,'f',{'a':5})
    def test_wrong_lineage(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cp.gz';save_cache(p,'f',{'a':4})
            with self.assertRaises(ValueError):load_cache(p,'g')
    def test_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cp.gz';save_cache(p,'f',{'a':4});v=json.loads(gzip.decompress(p.read_bytes()));v['payload']['a']=6;p.write_bytes(gzip.compress(json.dumps(v).encode()))
            with self.assertRaises(ValueError):load_cache(p,'f')
    def test_no_escaping_paths(self):
        with self.assertRaises(ValueError):inside(BASE,'../secret')
    def test_no_repeat_of_failed_stage(self):
        import run_lifecycle as run
        with tempfile.TemporaryDirectory() as d,patch.object(run,'OUT',Path(d)):
            write(Path(d)/'screen/status.json',{'status':'FAILED'})
            with self.assertRaises(RuntimeError):run.supervise('screen',Path(d))
    def test_no_activation_skips_all_branches(self):
        import run_lifecycle as run
        with tempfile.TemporaryDirectory() as d,patch.object(run,'OUT',Path(d)),patch.object(run,'preflight',return_value=(Path(d),None,'f')),patch.object(run,'verify_stage',return_value={'fingerprint':'f','selected_key':None}),patch.object(run,'log'):
            run.pilot(Path(d));self.assertEqual(read(Path(d)/'pilot/report.json')['completed_branches'],0)
