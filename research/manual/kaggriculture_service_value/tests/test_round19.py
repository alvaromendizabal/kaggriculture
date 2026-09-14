import unittest
from copy import deepcopy
from collection_features import describe,extract,score,timing,FIELDS,STATE_FIELDS
from tests.fixtures import observation,animal,GAME,job
class CollectionTests(unittest.TestCase):
 def row(self,obs=None,worker=0,op='HARVEST'):
  return describe(obs or observation(),GAME,worker,(4,4),op)
 def test_01_manual_near(self):self.assertEqual(timing(240,0,0)[6],1)
 def test_02_manual_far(self):self.assertEqual(timing(240,2,3)[6],6)
 def test_03_night_shortcut(self):self.assertEqual(timing(261,0,8)[6],3)
 def test_04_night_sell_not_current(self):self.assertEqual(timing(263,0,0)[6],1)
 def test_05_terminal_collect_not_sellable(self):self.assertEqual(timing(718,0,0)[6],-1)
 def test_06_penultimate_sellable(self):self.assertEqual(timing(717,0,0)[6],1)
 def test_07_cross_reset_arrival_unavailable(self):self.assertEqual(timing(263,1,0)[6],-1)
 def test_08_invalid_step(self):
  with self.assertRaises(ValueError):timing(719,0,0)
 def test_09_negative_travel(self):
  with self.assertRaises(ValueError):timing(0,-1,0)
 def test_10_negative_return(self):
  with self.assertRaises(ValueError):timing(0,0,-1)
 def test_11_task_schema(self):self.assertEqual(set(self.row()),set(FIELDS));self.assertEqual(len(FIELDS),32)
 def test_12_state_schema(self):self.assertEqual(set(extract(observation(),GAME)[1]),set(STATE_FIELDS));self.assertEqual(len(STATE_FIELDS),12)
 def test_13_quote_is_not_adjusted(self):self.assertEqual(self.row()['quoted_goods_value'],90)
 def test_14_return_geometry(self):self.assertEqual(self.row()['return_actions'],0)
 def test_15_score_nonincrease(self):self.assertLessEqual(self.row()['score_multiplier'],1)
 def test_16_denominator_nonshorter(self):r=self.row();self.assertGreaterEqual(r['candidate_denominator'],r['reference_denominator'])
 def test_17_input_immutable(self):o=observation();b=deepcopy(o);self.row(o);self.assertEqual(o,b)
 def test_18_seat_symmetry(self):self.assertEqual(self.row(observation(seat=0)),self.row(observation(seat=1)))
 def test_19_all_workers_kept(self):o=observation(hands=7);self.assertEqual(len(extract(o,GAME)[0]),8)
 def test_20_alignment_refused(self):
  o=observation();o['private']['inventories']=[]
  with self.assertRaises(ValueError):self.row(o)
 def test_21_absent_goods_refused(self):
  o=observation();o['farms'][0]['tiles'][4][4]['yield_units']=0
  with self.assertRaises(ValueError):self.row(o)
 def test_22_immature_crop_refused(self):
  o=observation();o['farms'][0]['tiles'][4][4]['planted_day']=10
  with self.assertRaises(ValueError):self.row(o)
 def test_23_livestock_goods(self):
  o=observation();o['farms'][0]['tiles'][4][4]=animal();self.assertEqual(self.row(o)['task_units'],3)
 def test_24_manure_one_unit(self):
  o=observation();o['farms'][0]['tiles'][4][4]=animal();self.assertEqual(self.row(o,op='COLLECT_FERTILIZER')['task_units'],1)
 def test_25_no_opponent_private_dependency(self):
  o=observation();a=self.row(o);o['farms'][1]={'private':{'WHEAT':999},'money':999};self.assertEqual(a,self.row(o))
 def test_26_no_seed_reward_dependency(self):
  o=observation();a=self.row(o);o.update(seed=987,reward=999,future={'prices':0});self.assertEqual(a,self.row(o))
 def test_27_terminal_score_unchanged(self):
  o=observation(day=29);f=o['farms'][0];self.assertEqual(score(o,GAME,f,o['private'],0,f['farmer'],job(),8),100/9)
 def test_28_unrelated_job_unchanged(self):
  o=observation();f=o['farms'][0];self.assertEqual(score(o,GAME,f,o['private'],0,f['farmer'],job('WATER'),8),100/9)
 def test_29_snapshot_overflow_diagnostic(self):
  o=observation();o['private']['shed']['WHEAT']=100;self.assertGreater(extract(o,GAME)[1]['capacity_stress_options'],0)
 def test_30_other_workers_not_joint_income(self):
  o=observation(hands=3);r=self.row(o);self.assertEqual(r['alternative_worker_count'],3);self.assertEqual(r['one_sided_liquidation'],90)
 def test_31_empty_tasks_safe(self):
  o=observation();o['farms'][0]['tiles'][4][4]=None;r,s=extract(o,GAME);self.assertFalse(r);self.assertEqual(s['task_options'],0)
 def test_32_night_and_manual_boundary(self):
  for hour in range(24):
   for d in range(10):
    night,left,manual,arr,mok,nok,off,den=timing(240+hour,d,3)
    self.assertGreaterEqual(den,d+1)
    if off>=0:self.assertTrue(mok or nok);self.assertLess(off,left)
