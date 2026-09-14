"""Notebook code/runner regressions; fake child commands do not run the game."""
import ast, contextlib, io, json, os, signal, subprocess, sys, tempfile, time, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def notebook():
    return json.loads((ROOT/'12_water_maintenance_feature_ablation.ipynb').read_text())

class NotebookTests(unittest.TestCase):
    def test_live_notebook_is_unexecuted_and_compiles(self):
        for c in notebook()['cells']:
            if c['cell_type']=='code':
                source=''.join(c['source'])
                ast.parse(source)
                self.assertIsNone(c.get('execution_count'))
                self.assertEqual(c.get('outputs'),[])
    def test_stage_runner_reports_failure(self):
        self.exercise(2)
    def test_stage_runner_streams_success(self):
        self.exercise(0)
    def exercise(self, exit_code):
        source=next(''.join(c['source']) for c in notebook()['cells'] if c['cell_type']=='code' and 'def run_stage' in ''.join(c['source']))
        fun=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='run_stage')
        module=ast.Module(body=[fun],type_ignores=[])
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);out=root/'outputs';(out/'screen').mkdir(parents=True)
            (out/'screen/report.json').write_text('{"status":"FAKE_CHILD_TEST"}')
            (root/'run_maintenance.py').write_text(f'import sys\nprint("FAKE_CHILD_HEARTBEAT",flush=True)\nsys.exit({exit_code})\n')
            ns={'ROOT':root,'OUT':out,'PYTHON_BIN':sys.executable,'subprocess':subprocess,'time':time,'os':os,'signal':signal,'json':json}
            exec(compile(module,'<test-notebook-runner>','exec'),ns)
            with contextlib.redirect_stdout(io.StringIO()) as capture:
                if exit_code:
                    with self.assertRaises(RuntimeError): ns['run_stage']('screen')
                else:
                    self.assertEqual(ns['run_stage']('screen')['status'],'FAKE_CHILD_TEST')
            self.assertIn('FAKE_CHILD_HEARTBEAT',capture.getvalue())
