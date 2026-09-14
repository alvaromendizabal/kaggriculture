import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run_milestone as runner

class RunnerTests(unittest.TestCase):
    def test_atomic_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.json';runner.write(p,{'a':1});self.assertEqual(runner.read(p),{'a':1})
    def test_atomic_rejects_nan(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.json';runner.write(p,{'a':1})
            with self.assertRaises(ValueError):runner.write(p,{'a':float('nan')})
            self.assertEqual(runner.read(p),{'a':1})
    def test_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cache.json';runner.save_cache(p,'abc',{'rows':[1,2]})
            self.assertEqual(runner.read_cache(p,'abc'),{'rows':[1,2]})
    def test_cache_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cache.json';runner.save_cache(p,'abc',{'rows':[1,2]})
            x=runner.read(p);x['payload']['rows']=[9];runner.write(p,x)
            with self.assertRaisesRegex(ValueError,'checksum'):runner.read_cache(p,'abc')
    def test_cache_wrong_source(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cache.json';runner.save_cache(p,'abc',{'a':1})
            with self.assertRaisesRegex(ValueError,'different'):runner.read_cache(p,'new')
    def test_missing_cache(self):
        with tempfile.TemporaryDirectory() as d:self.assertIsNone(runner.read_cache(Path(d)/'none','abc'))
    def test_path_escape(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):runner.contained(Path(d),'../outside')
    def test_path_absolute_escape(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):runner.contained(Path(d),'/etc/passwd')
    def test_output_source_validation(self):
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'OUT',Path(d)):
            runner.write(Path(d)/'report.json',{'status':runner.STATE_STATUS,'code_sha256':'wrong'})
            with self.assertRaises(ValueError):runner.verify_outputs()
    def test_output_checksum_validation(self):
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'OUT',Path(d)):
            p=Path(d)/'feature.csv';p.write_text('x\n1\n')
            runner.write(Path(d)/'report.json',{'status':runner.STATE_STATUS,'code_sha256':runner.code_digest(),'output_sha256':{'feature.csv':'wrong'}})
            with self.assertRaises(ValueError):runner.verify_outputs()

if __name__=='__main__':unittest.main()
