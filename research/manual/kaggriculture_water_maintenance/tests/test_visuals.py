import tempfile, unittest, json
from pathlib import Path
import pandas as pd
from visualize_maintenance import prior_figure, screen_figures, pilot_figures, dashboard

class PlotTests(unittest.TestCase):

    def test_all_plots_serialize(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'screen').mkdir()
            (p / 'pilot').mkdir()
            pd.DataFrame([dict(role='primary', coins_delta=-2, opponent_coins_delta=-3, coin_margin_delta=1)]).to_csv(p / 'notebook11_pairs.csv', index=False)
            states = [dict(day=20, seed=1601, seat=0, step=480, action_changed_in_window=True, deferred_next_day_tasks=2, unwatered_plants=3, candidate_callback_ms=2, plant_count=3, defer_eligible_plants=2)]
            pd.DataFrame(states).to_csv(p / 'screen/states.csv', index=False)
            pd.DataFrame([dict(crop='WHEAT', defer_eligible=1, survival_gain=0, water_bonus_now=0, next_units_delta=0, next_day_maintenance_debt=1, seed=1601, seat=0, day=20, hour=0, dry_streak=0)]).to_csv(p / 'screen/crop_features.csv.gz', index=False)
            (p / 'pilot/report.json').write_text(json.dumps({'completed_pairs': 0}))
            figs = [prior_figure(p), *screen_figures(p), *pilot_figures(p)]
            self.assertEqual(len(figs), 8)
            for f in figs:
                self.assertTrue(f.to_json())
            dashboard(figs, p / 'report.html')
            self.assertIn('plotly', (p / 'report.html').read_text())

    def test_endpoint_plots(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'pilot').mkdir()
            (p / 'pilot/report.json').write_text(json.dumps({'completed_pairs': 1}))
            pd.DataFrame([dict(coins_delta=2, coin_margin_delta=2, residual_product_units_delta=0)]).to_csv(p / 'pilot/paired_results.csv', index=False)
            pd.DataFrame([dict(step=480, mode=m, own_cash=3000, day=20, water_commands=1) for m in ('control', 'defer')]).to_csv(p / 'pilot/trajectories.csv', index=False)
            self.assertEqual(len(pilot_figures(p)), 2)
