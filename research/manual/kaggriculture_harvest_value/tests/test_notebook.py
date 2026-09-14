from pathlib import Path
import unittest,nbformat
class NotebookTests(unittest.TestCase):
    def test_structure(self):
        n=nbformat.read(Path(__file__).resolve().parents[1]/'14_harvest_value_feature_ablation.ipynb',as_version=4);nbformat.validate(n)
    def test_all_cells_compile(self):
        n=nbformat.read(Path(__file__).resolve().parents[1]/'14_harvest_value_feature_ablation.ipynb',as_version=4)
        for c in n.cells:
            if c.cell_type=='code':compile(c.source,'<notebook>','exec')
    def test_live_notebook_no_synthetic_results(self):
        n=nbformat.read(Path(__file__).resolve().parents[1]/'14_harvest_value_feature_ablation.ipynb',as_version=4)
        self.assertTrue(all(c.execution_count is None and not c.outputs for c in n.cells if c.cell_type=='code'))
