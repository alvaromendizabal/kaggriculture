"""Regression coverage for the real pricing mistake, using explicit narrow doubles.

The WHEAT quote below follows the public official formula. The transition is still
an explicit unit-test double, not the installed Kaggle interpreter. The runner's
mechanics() gate separately uses the hash-verified installed interpreter on AWS.
Source: Kaggle/kaggle-environments, envs/kaggriculture/kaggriculture.py,
MARKET_PARAMS['WHEAT'], _shape, market_price, _commit_unit.
"""
from copy import copy, deepcopy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import fixtures
from continuation import project_next
from mechanics_checks import KINDS, evaluate_fixture, quoted_sale
import run_continuation as runner


def documented_wheat_price(item, supply):
    if item != 'WHEAT':
        return 10
    if supply < 10000:
        p = 25 + (.8 * 25 / math.sqrt(400)) * math.sqrt(10000 - supply)
    else:
        p = 25 - (.2 * 25 / math.log(1 + 400)) * math.log(1 + supply - 10000)
    return max(1, int(round(p)))


class PricingRegression(unittest.TestCase):
    def setUp(self):
        self.game = copy(fixtures.GAME)
        self.game.market_price = documented_wheat_price
        self.quote_patch = patch.object(fixtures, 'price', documented_wheat_price)
        self.quote_patch.start()
    def tearDown(self):
        self.quote_patch.stop()
    def evaluate(self, kind, **kw):
        return evaluate_fixture(self.game, fixtures.transition, project_next, kind, **kw)
    def test_documented_quote_is_thirteen_not_one(self):
        self.assertEqual(documented_wheat_price('WHEAT', 1_000_000), 13)
    def test_two_units_are_twenty_six(self):
        self.assertEqual(quoted_sale(self.game, 'WHEAT', 1_000_000, 2),
                         {'revenue': 26, 'quotes': [13, 13], 'post_inventory': 1_000_002})
    def test_original_constant_two_assertion_would_fail(self):
        row = self.evaluate(KINDS[1])
        self.assertEqual(row['terminal_cash_delta'], 26)
        self.assertNotEqual(row['terminal_cash_delta'], 2)
    def test_late_sale_actual_and_expected_match(self):
        row = self.evaluate(KINDS[1]); self.assertTrue(row['passed'])
        self.assertEqual((row['control_final_cash'], row['aligned_final_cash']), (3000, 3026))
    def test_early_sale_is_only_acceleration(self):
        row = self.evaluate(KINDS[0]); self.assertTrue(row['passed'])
        self.assertEqual((row['control_final_cash'], row['aligned_final_cash']), (3026, 3026))
        self.assertEqual(row['expected_delta'], 0)
    def test_seat_one_late_fixture(self):
        row = self.evaluate(KINDS[1], seat=1)
        self.assertTrue(row['passed']); self.assertEqual(row['expected_delta'], 26)
    def test_seat_one_early_fixture(self):
        self.assertTrue(self.evaluate(KINDS[0], seat=1)['passed'])
    def test_actual_floor_has_two_coin_effect(self):
        row = self.evaluate(KINDS[1], inventory=10**15)
        self.assertTrue(row['passed']); self.assertEqual(row['initial_quote'], 1)
        self.assertEqual(row['expected_delta'], 2)
    def test_floor_does_not_increase_inventory(self):
        v = quoted_sale(self.game, 'WHEAT', 10**15, 2)
        self.assertEqual(v['post_inventory'], 10**15)
    def test_individual_unit_quotes_not_quantity_times_headline(self):
        self.game.market_price = lambda item, supply: {5: 3, 6: 2, 7: 1}[supply]
        self.assertEqual(quoted_sale(self.game, 'WHEAT', 5, 4),
                         {'revenue': 7, 'quotes': [3, 2, 1, 1], 'post_inventory': 7})
    def test_invalid_quantities(self):
        for q in (-1, 1.1, True, 101):
            with self.subTest(q=q), self.assertRaises(ValueError):
                quoted_sale(self.game, 'WHEAT', 1_000_000, q)
    def test_invalid_price_rejected(self):
        for p in (float('nan'), float('inf'), -1, 0, True):
            self.game.market_price = lambda *args, p=p: p
            with self.subTest(p=p), self.assertRaises(ValueError):
                quoted_sale(self.game, 'WHEAT', 1_000_000, 2)
    def test_zero_quantity(self):
        self.assertEqual(quoted_sale(self.game, 'WHEAT', 1_000_000, 0)['revenue'], 0)
    def test_reward_not_enough_if_money_wrong(self):
        def bad(*args):
            r = fixtures.transition(*args)
            for v in r: v['reward'] += 1
            return r
        row = evaluate_fixture(self.game, bad, project_next, KINDS[1])
        self.assertFalse(row['passed'])
    def test_input_mutation_fails_gate(self):
        def bad(own, rival, *args):
            r = fixtures.transition(own, rival, *args)
            own['private']['shed']['WHEAT'] = 99
            return r
        row = evaluate_fixture(self.game, bad, project_next, KINDS[1])
        self.assertFalse(row['passed'])
    def test_trace_contains_six_transition_diagnostics(self):
        row = self.evaluate(KINDS[1]); self.assertEqual(len(row['trace']), 6)
        self.assertEqual(row['interpreter_calls'], 6)
    def test_failed_fixture_saved_before_raise(self):
        def bad(*args):
            r = fixtures.transition(*args)
            if r[0]['status'] == 'DONE': r[0]['reward'] += 1
            return r
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner, 'OUT', Path(tmp)), patch.object(runner, 'log'):
            with self.assertRaisesRegex(ValueError, 'see outputs/mechanics.json'):
                runner.mechanics(self.game, bad)
            r = json.loads((Path(tmp)/'mechanics.json').read_text())
            self.assertFalse(r[0]['passed']); self.assertIn('per_unit_quotes', r[0])
    def test_runner_corrected_two_fixture_contract(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner, 'OUT', Path(tmp)), patch.object(runner, 'log'):
            rows = runner.mechanics(self.game, fixtures.transition)
            self.assertEqual([r['terminal_cash_delta'] for r in rows], [0, 26])
            self.assertTrue(all(r['passed'] for r in rows))


class ReviewedResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.out = patch.object(runner, 'OUT', self.root); self.out.start()
        self.logger = patch.object(runner, 'log'); self.logger.start()
        runner.write(self.root/'run_status.json', {'status': 'FAILED'})
        runner.write(self.root/'failure_worker.json', {'traceback': 'in mechanics\nValueError: Continuation fixture endpoint incorrect'})
        self.grant = {'update_id': 'nb09-price-aware-mechanics-1', 'code_sha256': runner.code_hash(),
                      'failed_status_sha256': runner.sha(self.root/'run_status.json'),
                      'failed_worker_sha256': runner.sha(self.root/'failure_worker.json')}
        runner.write(self.root/'resume_authorization.json', self.grant)
    def tearDown(self):
        self.out.stop(); self.logger.stop(); self.temp.cleanup()
    def test_known_failure_one_restart(self):
        runner.consume_reviewed_resume()
        self.assertTrue((self.root/'resume_authorization_used.json').exists())
    def test_second_restart_not_automatic(self):
        runner.consume_reviewed_resume()
        with self.assertRaises(RuntimeError): runner.consume_reviewed_resume()
    def test_modified_source_not_authorized(self):
        with patch.object(runner, 'code_hash', return_value='changed'):
            with self.assertRaises(RuntimeError): runner.consume_reviewed_resume()
    def test_modified_failure_not_authorized(self):
        runner.write(self.root/'failure_worker.json', {'traceback': 'different'})
        with self.assertRaises(RuntimeError): runner.consume_reviewed_resume()
    def test_missing_review_not_authorized(self):
        (self.root/'resume_authorization.json').unlink()
        with self.assertRaises(RuntimeError): runner.consume_reviewed_resume()
    def test_existing_branch_evidence_blocks_cross_code_resume(self):
        (self.root/'checkpoints').mkdir(); (self.root/'checkpoints'/'x.json.gz').write_bytes(b'preserve')
        with self.assertRaises(RuntimeError): runner.consume_reviewed_resume()
        self.assertEqual((self.root/'checkpoints'/'x.json.gz').read_bytes(), b'preserve')
    def test_existing_report_blocks_overwrite(self):
        runner.write(self.root/'report.json', {'status': 'preserve'})
        with self.assertRaises(RuntimeError): runner.consume_reviewed_resume()
