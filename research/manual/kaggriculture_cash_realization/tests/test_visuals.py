from pathlib import Path
import tempfile
import unittest
import pandas as pd
from visualize import charts,save_dashboard


def write_artificial_tables(root):
    """Synthetic reporting inputs; never represented as live experiment results."""
    pd.DataFrame([{'episode_id':'SYNTHETIC','step':718,'control_callback_ms':1.,'aligned_callback_ms':1.2}]).to_csv(root/'callback_checks.csv',index=False)
    pd.DataFrame([{'episode_id':'SYNTHETIC','step':718,'own_cash_delta':3,'seed':0,'seat':0,'source_arm':'coordinated',
                   'coin_margin_delta':3,'residual_units_delta':-1}]).to_csv(root/'one_step_effects.csv',index=False)
    pd.DataFrame([{'product':'WHEAT','undercoverage_present':1,'uncovered_sellable_units':1}]).to_csv(root/'product_features.csv',index=False)
    pd.DataFrame([{'feature':'cash.test','nonzero_fraction':1.,'distinct_values':1}]).to_csv(root/'feature_registry.csv',index=False)
    pd.DataFrame([{'seed':0,'arm':'full','changed_first_actions':0}]).to_csv(root/'notebook07_probe_by_episode.csv',index=False)

class PlotTests(unittest.TestCase):
    def test_six_distinct_plotly_figures(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);write_artificial_tables(root);figs=charts(root,root)
            self.assertEqual(len(figs),6)
            for f in figs:self.assertTrue(f.to_plotly_json()['data'])
    def test_offline_dashboard(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);write_artificial_tables(root);figs=charts(root,root)
            save_dashboard(figs,root/'test.html',heading='SYNTHETIC TEST — NOT RESULTS')
            text=(root/'test.html').read_text();self.assertIn('SYNTHETIC TEST',text);self.assertIn('plotly.js',text)
    def test_missing_result_files_not_silently_synthetic(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):charts(Path(d),Path(d))
