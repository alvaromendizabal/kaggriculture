import unittest
from types import SimpleNamespace
from copy import deepcopy
from unittest.mock import patch
from helpers import ToyEnv, payload, toy_factory, observation
from harvest_experiment import rollout, paired, decision, index_records, measure
from run_harvest import samples, select_source

class ExperimentTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data = payload()

    def test_sample_count(self):
        self.assertEqual(len(samples()), 52)

    def test_all_window_hours_sampled(self):
        self.assertTrue(set(range(480, 528)).issubset(samples()))

    def test_no_final_day_screen(self):
        self.assertNotIn(718, samples())

    def test_selection_not_outcome(self):
        rows = [dict(seed=s, seat=0, opponent='livestock_fertilizer', arm='coordinated', action_changed_in_window=True, coins_delta=999 if s == 1602 else -5) for s in (1602, 1601)]
        self.assertEqual(select_source(rows)['seed'], 1601)

    def test_nonactivation(self):
        self.assertIsNone(select_source([]))

    def test_duplicate_records(self):
        d = {'records': [self.data['records'][0], self.data['records'][0]]}
        with self.assertRaises(ValueError):
            index_records(d)

    def test_incomplete_records(self):
        with self.assertRaises(ValueError):
            index_records({'records': self.data['records'][:-1]})

    def test_actor_mutation(self):

        def actor(o):
            o['day'] = 0
            return {}
        with self.assertRaises(ValueError):
            measure(actor, observation(), 'x', lambda *a: None)

    def test_latency_saved_before_reject(self):
        events = []
        with patch('harvest_experiment.time.perf_counter', side_effect=[0, 1]), self.assertRaises(RuntimeError):
            measure(lambda o: {}, observation(), 'x', lambda *a: events.append(a))
        self.assertEqual(len(events), 1)

    def test_live_prefix_and_linked_suffix_toy(self):
        for seat in (0, 1):
            key = dict(seed=1601, seat=seat, opponent='livestock_fertilizer', arm='coordinated')
            results = []
            for mode in ('control', 'marginal'):
                results.append(rollout(self.data, key, mode, SimpleNamespace(PRODUCTS=['WHEAT']), lambda seed: ToyEnv(), dict(coins_guarded=3000.0, opponent_coins_guarded=3000.0), lambda *a: None, lambda *a, **k: None, toy_factory))
            row = paired(*results)
            self.assertEqual(row['coins_delta'], 2)
            self.assertEqual(results[0]['prefix_replay_transitions'], 480)
            self.assertEqual(results[1]['trace'][-1]['own_cash'], 3002)
            self.assertEqual(decision(row), 'PROMISING_SINGLE_DEVELOPMENT_PAIR_REQUIRES_VALIDATION')

    def test_negative_endpoint_even_margin_positive(self):
        self.assertEqual(decision({'coins_delta': -2, 'coin_margin_delta': 1, 'local_match_score_delta': 0, 'same_state_action_changes': 2}), 'STOP_NEGATIVE_ENDPOINT')

    def test_empty_effect(self):
        self.assertEqual(decision({'coins_delta': 0, 'coin_margin_delta': 0, 'local_match_score_delta': 0, 'same_state_action_changes': 2}), 'STOP_NO_ENDPOINT_BENEFIT')

    def test_partial_cannot_score(self):
        with self.assertRaises((ValueError, KeyError)):
            paired({'key': {}, 'initial_sha256': 'x', 'mode': 'control', 'suffix_transitions': 1}, {'key': {}, 'initial_sha256': 'x', 'mode': 'marginal'})
