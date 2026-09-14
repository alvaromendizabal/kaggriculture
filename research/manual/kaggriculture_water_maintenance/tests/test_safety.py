import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from helpers import ToyEnv, payload, toy_factory
from maintenance_experiment import rollout, paired
from run_maintenance import supervise

class SafetyTests(unittest.TestCase):

    def test_failed_stage_not_retried(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / 'screen').mkdir()
            p = out / 'screen/status.json'
            p.write_text('{"status":"FAILED"}')
            with patch('run_maintenance.OUT', out), patch('run_maintenance.subprocess.Popen') as launch, self.assertRaises(RuntimeError):
                supervise('screen', out)
            launch.assert_not_called()
            self.assertEqual(json.loads(p.read_text())['status'], 'FAILED')

    def test_running_stage_not_retried(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / 'screen').mkdir()
            (out / 'screen/status.json').write_text('{"status":"RUNNING"}')
            with patch('run_maintenance.OUT', out), patch('run_maintenance.subprocess.Popen') as launch, self.assertRaises(RuntimeError):
                supervise('screen', out)
            launch.assert_not_called()

    def test_responsive_toy_opponent_uses_changed_state(self):
        data = payload()
        key = dict(seed=1601, seat=0, opponent='livestock_fertilizer', arm='coordinated')

        def factory(game, mode, seat, arm):
            c, r, n, _ = toy_factory(game, mode, seat, arm)

            def rival(obs):
                if obs['step'] == 481 and obs['farms'][1 - obs['player']]['money'] > 3000:
                    return {'farmer': ['PASS'], 'hands': [], 'market': [['TOY_CASH', 1]]}
                return {'farmer': ['PASS'], 'hands': [], 'market': []}
            return (c, r, n, rival)
        branches = [rollout(data, key, mode, SimpleNamespace(PRODUCTS=['WHEAT']), lambda seed: ToyEnv(), dict(coins_guarded=3000.0, opponent_coins_guarded=3000.0), lambda *a: None, lambda *a, **k: None, factory) for mode in ('control', 'defer')]
        effect = paired(*branches)
        self.assertEqual(effect['opponent_coins_delta'], 1)
        self.assertEqual(effect['coin_margin_delta'], 1)

    def test_changed_source_prefix_rejected(self):
        data = payload()
        data['records'][0]['observation']['farms'][0]['money'] = 2999
        key = dict(seed=1601, seat=0, opponent='livestock_fertilizer', arm='coordinated')
        with self.assertRaises(ValueError):
            rollout(data, key, 'control', SimpleNamespace(PRODUCTS=['WHEAT']), lambda seed: ToyEnv(), dict(coins_guarded=3000.0, opponent_coins_guarded=3000.0), lambda *a: None, lambda *a, **k: None, toy_factory)
