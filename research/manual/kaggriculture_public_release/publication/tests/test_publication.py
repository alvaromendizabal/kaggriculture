"""Run these local fixture tests yourself before prepare. No real accounts touched."""
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import publish

class PublicReleaseSafety(unittest.TestCase):
    def test_expected_https(self):
        self.assertTrue(publish.remote_ok('https://github.com/alvaromendizabal/kaggriculture.git'))
    def test_expected_ssh(self):
        self.assertTrue(publish.remote_ok('git@github.com:alvaromendizabal/kaggriculture.git'))
    def test_other_repository_rejected(self):
        self.assertFalse(publish.remote_ok('https://github.com/another/kaggriculture.git'))
    def test_credential_url_rejected(self):
        self.assertFalse(publish.remote_ok('https://example@github.com/alvaromendizabal/kaggriculture.git'))
    def test_parent_escape(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): publish.inside(Path(d), '../outside')
    def test_absolute_escape(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): publish.inside(Path(d), '/etc/passwd')
    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'link').symlink_to('/tmp')
            with self.assertRaises(ValueError): publish.inside(root, 'link/file')
    def test_safe_relative(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(publish.inside(Path(d), 'src/a.py'), Path(d)/'src/a.py')
    def test_source_included(self):
        self.assertTrue(publish.allowed(Path('src/policy.py')))
    def test_notebook_included(self):
        self.assertTrue(publish.allowed(Path('notebooks/report.ipynb')))
    def test_raw_excluded(self):
        self.assertFalse(publish.allowed(Path('raw/episode.json')))
    def test_runtime_excluded(self):
        self.assertFalse(publish.allowed(Path('.venv/lib/source.py')))
    def test_credentials_excluded(self):
        self.assertFalse(publish.allowed(Path('kaggle.json')))
    def test_env_excluded(self):
        self.assertFalse(publish.allowed(Path('.env.local')))
    def test_checkpoint_excluded(self):
        self.assertFalse(publish.allowed(Path('outputs/checkpoints/game.json')))
    def test_summary_included(self):
        self.assertTrue(publish.allowed(Path('outputs/round19/summary.json')))
    def test_trace_excluded(self):
        self.assertFalse(publish.allowed(Path('outputs/callback_trace.jsonl')))
    def test_secret_detection(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.txt'; p.write_text('gh'+'p_'+'a'*36)
            self.assertIn('github_token', publish.scan(p))
    def test_source_regex_is_not_secret(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ok.py'; p.write_text("AWS_PREFIX = 'AK' + 'IA'\n")
            self.assertEqual(publish.scan(p), [])
    def test_existing_different_destination_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a'; b=Path(d)/'b'; a.write_text('new'); b.write_text('keep')
            with self.assertRaises(ValueError): publish.copy_checked(a,b,publish.digest(a))
            self.assertEqual(b.read_text(),'keep')
    def test_copy_readback(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a'; b=Path(d)/'b'; a.write_text('hello')
            publish.copy_checked(a,b,publish.digest(a)); self.assertEqual(a.read_bytes(),b.read_bytes())
    def test_copy_same_bytes_reuse(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a'; b=Path(d)/'b'; a.write_text('hello'); b.write_text('hello')
            publish.copy_checked(a,b,publish.digest(a)); self.assertEqual(b.read_text(),'hello')
    def test_stale_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a'; a.write_text('hello')
            with self.assertRaises(ValueError): publish.copy_checked(a,Path(d)/'b','0'*64)
    def test_notebook_status_not_invented(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'n.ipynb'; p.write_text(json.dumps({'cells':[{'cell_type':'code','source':['x=1'],'execution_count':None,'outputs':[]}]}))
            r=publish.notebook_info(p); self.assertEqual(r['saved_execution_counts'],0)
            self.assertIn('unexecuted',r['status'])

if __name__ == '__main__': unittest.main()
