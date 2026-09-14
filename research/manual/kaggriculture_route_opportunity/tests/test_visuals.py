import tempfile,unittest
from pathlib import Path
import pandas as pd
from route_io import write
from visualize_routes import screen_figures,pilot_figures,dashboard

class PlotTests(unittest.TestCase):
    def setUp(self):self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);(self.root/'screen').mkdir()
    def tearDown(self):self.t.cleanup()
    def base_screen(self):
        pd.DataFrame([{'seed':1601,'seat':0,'step':696,'farm_commands_changed':False,'static_utility_delta':0,'candidate_callback_ms':1}]).to_csv(self.root/'screen/states.csv',index=False)
        pd.DataFrame([{'feature':'route.actions','nonzero_fraction':0.}]).to_csv(self.root/'screen/feature_registry.csv',index=False)
    def test_no_routes_plot(self):
        import gzip
        self.base_screen();(self.root/'screen/route_candidates.csv.gz').write_bytes(gzip.compress(b'\n'))
        self.assertEqual(len(screen_figures(self.root)),5)
    def test_no_activation_plot(self):
        write(self.root/'pilot/report.json',{'decision':'STOP_NO_ACTION_ACTIVATION','completed_pairs':0})
        self.assertEqual(len(pilot_figures(self.root)),2)
    def test_positive_pilot_plots(self):
        write(self.root/'pilot/report.json',{'decision':'SYNTHETIC_TEST','completed_pairs':1})
        pd.DataFrame([{'role':'primary','seed':1601,'seat':0,'coins_delta':2,'coin_margin_delta':2}]).to_csv(self.root/'pilot/paired_results.csv',index=False)
        pd.DataFrame([{'arm':'coordinated','step':696,'mode':m,'own_cash':100} for m in ('control','opportunity')]).to_csv(self.root/'pilot/trajectories.csv',index=False)
        self.assertEqual(len(pilot_figures(self.root)),2)
    def test_dashboard_is_self_contained(self):
        write(self.root/'pilot/report.json',{'decision':'STOP_NO_ACTION_ACTIVATION','completed_pairs':0})
        dashboard(pilot_figures(self.root),self.root/'dashboard.html')
        self.assertIn('plotly.js',(self.root/'dashboard.html').read_text());self.assertGreater((self.root/'dashboard.html').stat().st_size,100000)
