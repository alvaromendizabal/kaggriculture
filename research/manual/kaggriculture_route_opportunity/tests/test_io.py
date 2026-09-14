import gzip,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from route_io import *

class IOTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_roundtrip(self):
        p=self.root/'a.gz';save_cache(p,'x',{'n':2});self.assertEqual(load_cache(p,'x'),{'n':2})
    def test_missing_is_not_success(self):self.assertIsNone(load_cache(self.root/'a','x'))
    def test_corrupt(self):
        p=self.root/'a';save_cache(p,'x',{'n':2});d=json.loads(gzip.decompress(p.read_bytes()));d['payload']['n']=3;p.write_bytes(gzip.compress(canonical(d)))
        with self.assertRaises(ValueError):load_cache(p,'x')
    def test_lineage(self):
        p=self.root/'a';save_cache(p,'x',2)
        with self.assertRaises(ValueError):load_cache(p,'y')
    def test_do_not_overwrite(self):
        p=self.root/'a';save_cache(p,'x',2);before=p.read_bytes()
        with self.assertRaises(ValueError):save_cache(p,'x',3)
        self.assertEqual(p.read_bytes(),before)
    def test_path_escape(self):
        with self.assertRaises(ValueError):inside(self.root,'../escape')
    def test_nan_rejected(self):
        with self.assertRaises(ValueError):canonical({'x':float('nan')})
    def test_atomic_read(self):
        write(self.root/'a.json',{'b':1});self.assertEqual(read(self.root/'a.json'),{'b':1})
    def test_outputs_not_source_code(self):
        (self.root/'x.py').write_text('x=1');before=code_hash(self.root);(self.root/'outputs').mkdir();(self.root/'outputs/y.py').write_text('y=1');self.assertEqual(code_hash(self.root),before)
    def test_source_change_invalidates(self):
        p=self.root/'a.py';p.write_text('a=1');before=code_hash(self.root);p.write_text('a=2');self.assertNotEqual(code_hash(self.root),before)
