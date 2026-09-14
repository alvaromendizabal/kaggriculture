import unittest
from copy import deepcopy
from relative_features import augment,MAINTENANCE_FIELDS
from outcome_fixtures import maintenance as row
class MaintenanceContracts(unittest.TestCase):
    def test_01_count(self):self.assertEqual(len(MAINTENANCE_FIELDS),12)
    def test_02_empty(self):self.assertEqual(augment([],'20'),[])
    def test_03_immutable(self):
        r=[row()];old=deepcopy(r);augment(r,'20');self.assertEqual(r,old)
    def test_04_slack_gap(self):
        a=augment([row(),row(x=2,completion_slack=0)],'20');self.assertEqual(a[0]['slack_above_most_urgent'],2)
    def test_05_no_critical(self):self.assertEqual(augment([row(eligible_critical_job=0)],'20')[0]['peer_minimum_critical_slack'],-1)
    def test_06_critical_count(self):
        a=augment([row(),row(x=2,eligible_critical_job=0)],'20');self.assertEqual(a[0]['peer_critical_option_count'],1)
    def test_07_seed_isolation(self):
        a=augment([row(),row(seed=2)],'20');self.assertTrue(all(r['peer_due_option_count']==1 for r in a))
    def test_08_seat_isolation(self):
        a=augment([row(),row(seat=1)],'20');self.assertTrue(all(r['peer_due_option_count']==1 for r in a))
    def test_09_mode_isolation(self):
        a=augment([row(mode='control'),row(mode='candidate')],'20');self.assertTrue(all(r['peer_due_option_count']==1 for r in a))
    def test_10_feed_blocked(self):self.assertEqual(augment([row(operation='FEED')],'20')[0]['feed_blocked_with_shed_stock'],1)
    def test_11_wheat_surplus(self):self.assertEqual(augment([row(operation='FEED',worker_wheat=3)],'20')[0]['worker_wheat_minus_due_feed_jobs'],2)
    def test_12_survival_buffer(self):self.assertEqual(augment([row()],'20')[0]['additional_missed_refreshes_to_loss'],1)
    def test_13_serviced_buffer(self):self.assertEqual(augment([row(already_serviced=1)],'20')[0]['additional_missed_refreshes_to_loss'],2)
    def test_14_conditional_yield(self):self.assertEqual(augment([row(survival_critical=0)],'20')[0]['conditional_next_yield_at_survival_risk'],0)
    def test_15_nonfinite(self):
        with self.assertRaises(ValueError):augment([row(urgency_multiplier=float('inf'))],'20')
    def test_16_no_outcomes(self):
        with self.assertRaises(ValueError):augment([row(outcome='WIN')],'20')
if __name__=='__main__':unittest.main()
