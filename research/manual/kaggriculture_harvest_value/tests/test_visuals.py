from pathlib import Path
import unittest,tempfile
from visualize import reference_figures,dashboard
class VisualTests(unittest.TestCase):
    def test_actual_reference_charts(self):
        fs=reference_figures(Path(__file__).resolve().parents[1]);self.assertEqual(len(fs),2)
        for f in fs:self.assertTrue(f.to_plotly_json()['data'])
    def test_standalone_html(self):
        with tempfile.TemporaryDirectory() as d:
            p=dashboard(reference_figures(Path(__file__).resolve().parents[1]),Path(d)/'review.html')
            self.assertIn('plotly',p.read_text().lower())
