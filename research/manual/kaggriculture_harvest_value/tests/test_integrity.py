from pathlib import Path
import tempfile,json,gzip,unittest
from research_io import *
from mechanics import validate
from price_adapter import GAME
BASE=Path(__file__).resolve().parents[1]
class IntegrityTests(unittest.TestCase):
    def test_reference_ledger_reconciles(self):
        r=read(BASE/'reference/notebook13_report.json');self.assertEqual(sum(x['cash_delta'] for x in r['cash_decomposition'] if x['player']==0),-396)
    def test_reference_same_milk_quantity(self):
        r=read(BASE/'reference/notebook13_report.json');m=next(x for x in r['cash_decomposition'] if x['player']==0 and x['operation']=='SELL' and x['item']=='MILK');self.assertEqual((m['units_control'],m['units_defer'],m['cash_delta']),(28,28,-465))
    def test_checksum_roundtrip(self):
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
            p=Path(d)/'cp.gz';save_cache(p,'f',{'a':4});o=json.loads(gzip.decompress(p.read_bytes()));o['payload']['a']=5;p.write_bytes(gzip.compress(json.dumps(o).encode()))
            with self.assertRaises(ValueError):load_cache(p,'f')
    def test_escape_refused(self):
        with self.assertRaises(ValueError):inside(BASE,'../secret')
    def test_independent_adapter_mechanics_harness(self):
        r=validate(GAME);self.assertEqual((r['sale_cases'],r['demand_cases']),(405,189))
    def test_no_unchanged_stage_retry(self):
        import run_harvest as mod
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d,patch.object(mod,'OUT',Path(d)):
            write(Path(d)/'screen/status.json',{'status':'FAILED'})
            with self.assertRaises(RuntimeError):mod.supervise('screen',Path(d))
