import ast, tempfile, unittest
from pathlib import Path
from copy import deepcopy
from maintenance_policy import transform_call, ACTIVE_DAYS
from maintenance_io import save_cache, load_cache, write, read, inside, digest, code_hash
SOURCE = "def __call__(self, observation):\n    obs = observation\n    tile = obs['tile']\n    jobs = ['HARVEST']\n    if not tile['watered_today']:\n        jobs.append('WATER')\n    return jobs\n"

class PolicyTests(unittest.TestCase):

    def test_exactly_one_change(self):
        t = transform_call(SOURCE)
        calls = [n for n in ast.walk(t) if isinstance(n, ast.Name) and n.id == '__water_gate']
        self.assertEqual(len(calls), 1)

    def test_no_predicate_rejected(self):
        with self.assertRaises(ValueError):
            transform_call('def f():\n return 1')

    def test_multiple_rejected(self):
        with self.assertRaises(ValueError):
            transform_call(SOURCE + '\n' + SOURCE.replace('__call__', 'other'))

    def test_null_same(self):
        old = {}
        new = {'__water_gate': lambda t, o: not t['watered_today']}
        exec(SOURCE, old)
        exec(compile(transform_call(SOURCE), '<test>', 'exec'), new)
        for v in (False, True):
            self.assertEqual(old['__call__'](None, {'tile': {'watered_today': v}}), new['__call__'](None, {'tile': {'watered_today': v}}))

    def test_other_jobs_preserved(self):
        d = {'__water_gate': lambda t, o: False}
        exec(compile(transform_call(SOURCE), '<test>', 'exec'), d)
        self.assertEqual(d['__call__'](None, {'tile': {'watered_today': False}}), ['HARVEST'])

    def test_window_fixed(self):
        self.assertEqual(ACTIVE_DAYS, (20, 21))

class IOTests(unittest.TestCase):

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 's.json.gz'
            save_cache(p, 'f', {'a': 1})
            self.assertEqual(load_cache(p, 'f'), {'a': 1})

    def test_overwrite_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 's.gz'
            save_cache(p, 'f', {})
            with self.assertRaises(ValueError):
                save_cache(p, 'f', {})

    def test_fingerprint_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 's.gz'
            save_cache(p, 'f', {})
            with self.assertRaises(ValueError):
                load_cache(p, 'g')

    def test_path_escape(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                inside(d, '../outside')

    def test_digest_nan(self):
        with self.assertRaises(ValueError):
            digest({'x': float('nan')})

    def test_json_atomic(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'a.json'
            write(p, {'a': 2})
            self.assertEqual(read(p), {'a': 2})
