import unittest,json,ast,tempfile
from pathlib import Path
from unittest.mock import patch
from artifact_io import write
from run_diagnosis import supervise
BASE=Path(__file__).resolve().parents[1]
class NotebookAndSafetyTests(unittest.TestCase):
    def test_notebook_structure(self):
        import nbformat
        nb=nbformat.read(BASE/'13_maintenance_loss_and_interaction_features.ipynb',as_version=4);nbformat.validate(nb)
        self.assertEqual(len([c for c in nb.cells if c.cell_type=='code']),10)
    def test_notebook_sources_compile(self):
        nb=json.loads((BASE/'13_maintenance_loss_and_interaction_features.ipynb').read_text())
        for c in nb['cells']:
            if c['cell_type']=='code':compile(''.join(c['source']),'<notebook>','exec')
    def test_runtime_modules_compile(self):
        for p in BASE.glob('*.py'):compile(p.read_text(),str(p),'exec')
    def test_failed_stage_cannot_retry(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);write(out/'status.json',{'status':'FAILED'})
            with patch('run_diagnosis.OUT',out):
                with self.assertRaisesRegex(RuntimeError,'no unchanged retry'):supervise(Path.home())
    def test_initial_review_plots(self):
        from visualize import figures
        self.assertEqual(len(figures(BASE)),2)
