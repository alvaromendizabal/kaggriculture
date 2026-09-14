import unittest
from copy import deepcopy
from maintenance_features import describe,extract,score,urgency,FIELDS,STATE_FIELDS
from tests.fixtures import observation,animal,GAME,job
class MaintenanceTests(unittest.TestCase):
 def row(self,o=None,w=0,op='WATER'):return describe(o or observation(),GAME,w,(4,4),op)
 def test_01_no_travel_multiplier(self):self.assertEqual(urgency(12,0,True,True,True),1)
 def test_02_slack_multiplier(self):self.assertEqual(urgency(12,8,True,True,True),3)
 def test_03_last_feasible_multiplier(self):self.assertEqual(urgency(12,11,True,True,True),12)
 def test_04_unreachable_no_boost(self):self.assertEqual(urgency(12,12,True,True,True),1)
 def test_05_noncritical_no_boost(self):self.assertEqual(urgency(12,8,False,True,True),1)
 def test_06_no_resource_no_boost(self):self.assertEqual(urgency(12,8,True,False,True),1)
 def test_07_no_refresh_no_boost(self):self.assertEqual(urgency(12,8,True,True,False),1)
 def test_08_invalid_night(self):
  with self.assertRaises(ValueError):urgency(0,0,True,True,True)
 def test_09_invalid_travel(self):
  with self.assertRaises(ValueError):urgency(12,-1,True,True,True)
 def test_10_invalid_night_high(self):
  with self.assertRaises(ValueError):urgency(25,0,True,True,True)
 def test_11_task_schema(self):self.assertEqual(set(self.row()),set(FIELDS));self.assertEqual(len(FIELDS),32)
 def test_12_state_schema(self):self.assertEqual(set(extract(observation(),GAME)[1]),set(STATE_FIELDS));self.assertEqual(len(STATE_FIELDS),12)
 def test_13_wet_not_critical(self):
  o=observation();o['farms'][0]['tiles'][4][4]['watered_today']=True;self.assertEqual(self.row(o)['survival_critical'],0)
 def test_14_dry_zero_not_critical(self):
  o=observation();o['farms'][0]['tiles'][4][4]['consecutive_unwatered']=0;self.assertEqual(self.row(o)['survival_critical'],0)
 def test_15_unfed_critical(self):
  o=observation();o['farms'][0]['tiles'][4][4]=animal();self.assertEqual(self.row(o,op='FEED')['survival_critical'],1)
 def test_16_feed_empty_hand_not_available(self):
  o=observation();o['farms'][0]['tiles'][4][4]=animal();self.assertEqual(self.row(o,op='FEED')['resource_available'],0)
 def test_17_shed_food_not_carried(self):
  o=observation();o['farms'][0]['tiles'][4][4]=animal();o['private']['shed']['WHEAT']=50;self.assertEqual(self.row(o,op='FEED')['eligible_critical_job'],0)
 def test_18_carried_food_eligible(self):
  o=observation();o['farms'][0]['tiles'][4][4]=animal();o['private']['inventories'][0]['WHEAT']=1;self.assertEqual(self.row(o,op='FEED')['eligible_critical_job'],1)
 def test_19_feed_other_worker_requires_food(self):
  o=observation();o['farms'][0]['tiles'][4][4]=animal();self.assertEqual(self.row(o,op='FEED')['alternative_ready_workers'],0)
 def test_20_feed_other_worker_with_food(self):
  o=observation();o['farms'][0]['tiles'][4][4]=animal();o['private']['inventories'][1]['WHEAT']=1;self.assertEqual(self.row(o,op='FEED')['alternative_ready_workers'],1)
 def test_21_input_immutable(self):o=observation();b=deepcopy(o);self.row(o);self.assertEqual(o,b)
 def test_22_seat_symmetry(self):self.assertEqual(self.row(observation(seat=0)),self.row(observation(seat=1)))
 def test_23_all_workers_kept(self):self.assertEqual(len(extract(observation(hands=7),GAME)[0]),8)
 def test_24_alignment_refused(self):
  o=observation();o['private']['inventories']=[]
  with self.assertRaises(ValueError):self.row(o)
 def test_25_wrong_operation(self):
  with self.assertRaises(ValueError):self.row(op='HARVEST')
 def test_26_no_opponent_dependency(self):
  o=observation();a=self.row(o);o['farms'][1]={'private':{'MILK':99}};self.assertEqual(a,self.row(o))
 def test_27_no_future_dependency(self):
  o=observation();a=self.row(o);o.update(seed=432,reward=200,future={'rain':True});self.assertEqual(a,self.row(o))
 def test_28_day29_unchanged(self):
  o=observation(day=29);f=o['farms'][0];self.assertEqual(score(o,GAME,f,o['private'],0,f['farmer'],job('WATER'),8),100/9)
 def test_29_harvest_unchanged(self):
  o=observation();f=o['farms'][0];self.assertEqual(score(o,GAME,f,o['private'],0,f['farmer'],job('HARVEST'),8),100/9)
 def test_30_no_job_is_removed(self):
  o=observation();r,s=extract(o,GAME);o['farms'][0]['tiles'][4][4]['consecutive_unwatered']=0;r2,s2=extract(o,GAME);self.assertEqual(len(r),len(r2))
 def test_31_bounded_multiplier(self):
  for n in range(1,25):
   for d in range(19):self.assertTrue(1<=urgency(n,d,True,True,True)<=24)
 def test_32_empty_tasks_safe(self):
  o=observation();o['farms'][0]['tiles'][4][4]=None;r,s=extract(o,GAME);self.assertFalse(r);self.assertEqual(s['task_options'],0)
