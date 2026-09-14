import unittest
from copy import deepcopy
from relative_features import augment,COLLECTION_FIELDS
from outcome_fixtures import collection as row
class CollectionContracts(unittest.TestCase):
    def test_01_count(self):self.assertEqual(len(COLLECTION_FIELDS),12)
    def test_02_empty(self):self.assertEqual(augment([],'19'),[])
    def test_03_immutable(self):
        r=[row()];old=deepcopy(r);augment(r,'19');self.assertEqual(r,old)
    def test_04_singleton(self):self.assertEqual(augment([row()],'19')[0]['peer_best_other_cash_rate'],0)
    def test_05_best_gap(self):
        a=augment([row(),row(x=2,conditional_value_per_callback=20)],'19');self.assertEqual(a[0]['cash_rate_gap_to_best'],10)
    def test_06_competition_ties(self):
        a=augment([row(),row(x=2)],'19');self.assertEqual([r['cash_rate_competition_rank'] for r in a],[1,1])
    def test_07_seed_isolation(self):
        a=augment([row(),row(seed=2)],'19');self.assertTrue(all(r['peer_option_count']==1 for r in a))
    def test_08_seat_isolation(self):
        a=augment([row(),row(seat=1)],'19');self.assertTrue(all(r['peer_option_count']==1 for r in a))
    def test_09_clock_isolation(self):
        a=augment([row(),row(step=4)],'19');self.assertTrue(all(r['peer_option_count']==1 for r in a))
    def test_10_mode_isolation(self):
        a=augment([row(mode='control'),row(mode='candidate')],'19');self.assertTrue(all(r['peer_option_count']==1 for r in a))
    def test_11_missing_key(self):
        r=row();r.pop('worker')
        with self.assertRaises(ValueError):augment([r],'19')
    def test_12_nonfinite(self):
        with self.assertRaises(ValueError):augment([row(conditional_value_per_callback=float('nan'))],'19')
    def test_13_effort_positive(self):
        with self.assertRaises(ValueError):augment([row(candidate_denominator=0)],'19')
    def test_14_zero_total(self):self.assertEqual(augment([row(conditional_value_per_callback=0)],'19')[0]['conditional_cash_rate_share'],0)
    def test_15_availability_mask(self):self.assertEqual(augment([row(manual_sale_available=0)],'19')[0]['night_minus_manual_sale_offset'],0)
    def test_16_no_outcomes(self):
        with self.assertRaises(ValueError):augment([row(reward=999)],'19')
if __name__=='__main__':unittest.main()
