import unittest
from copy import deepcopy
from interaction_features import *
from helpers import CROPS,tile,observation,component_path
class FeaturesTests(unittest.TestCase):
    def test_cap_masks_interaction(self):
        r=plant_features(tile(),observation(),(1,1),[[1,1]],CROPS)
        self.assertEqual(r['water_gain_without_harvest'],0);self.assertEqual(r['water_gain_with_harvest'],1);self.assertEqual(r['cap_masked_water_gain'],1)
    def test_no_fertilizer_complement(self):
        r=plant_features(tile(fertilized_until_day=-1),observation(),(1,1),[[1,1]],CROPS)
        self.assertEqual(r['water_gain_with_harvest'],0)
    def test_hour23_unavailable(self):
        r=plant_features(tile(),observation(hour=23),(1,1),[[1,1]],CROPS);self.assertEqual(r['scenario_available'],0)
    def test_final_day_masks(self):
        r=plant_features(tile(),observation(day=29,hour=22),(1,1),[[1,1]],CROPS)
        self.assertEqual(r['scenario_available'],0);self.assertEqual(r['two_refresh_available'],0)
    def test_two_night_survival_buffer(self):
        r=plant_features(tile(),observation(),(1,1),[[1,1]],CROPS)
        self.assertEqual(r['two_refresh_survival_buffer_gain'],1)
    def test_already_watered_deadline(self):
        r=plant_features(tile(watered_today=True),observation(),(1,1),[[1,1]],CROPS);self.assertEqual(r['current_water_deadline_callbacks'],72)
    def test_urgent_deadline(self):
        r=plant_features(tile(consecutive_unwatered=1),observation(hour=22),(1,1),[[9,9]],CROPS)
        self.assertEqual(r['current_water_deadline_callbacks'],2);self.assertLess(r['current_water_deadline_slack'],0)
    def test_nearest_workers(self):
        r=plant_features(tile(),observation(),(1,1),[[9,9],[1,2],[1,1]],CROPS);self.assertEqual(r['nearest_worker_travel'],0);self.assertEqual(r['second_worker_travel'],1)
    def test_unbounded_worker_count(self):
        o=observation();o['farms'][0]['hands']=[[1,1]]*20
        _,s=extract(o,CROPS);self.assertEqual(s['workers'],21)
    def test_both_seats(self):
        a=extract(observation(player=0),CROPS);b=extract(observation(player=1),CROPS);self.assertEqual(a,b)
    def test_mutation(self):
        o=observation();b=deepcopy(o);extract(o,CROPS);self.assertEqual(o,b)
    def test_ignored_outcomes_and_private(self):
        o=observation();a=extract(o,CROPS);o.update(reward=9e9,seed=987,private={'nonsense':123},future_actions=['HARVEST']);self.assertEqual(a,extract(o,CROPS))
    def test_other_farm_private_ignored(self):
        o=observation();a=extract(o,CROPS);o['farms'][1]['secret_inventory']={'WHEAT':999};self.assertEqual(a,extract(o,CROPS))
    def test_schema(self):
        rows,s=extract(observation(),CROPS);self.assertEqual(len(FIELDS),22);self.assertEqual(set(s),set(SUMMARY_FIELDS));self.assertTrue(set(FIELDS)<=set(rows[0]))
    def test_bad_clock(self):
        o=observation();o['step']=1
        with self.assertRaises(ValueError):extract(o,CROPS)
    def test_bad_coordinate(self):
        with self.assertRaises(ValueError):plant_features(tile(),observation(),(1,1),[[10,2]],CROPS)
    def test_missing_worker(self):
        with self.assertRaises(ValueError):plant_features(tile(),observation(),(1,1),[],CROPS)
    def test_bad_tile(self):
        with self.assertRaises(ValueError):plant_features(tile(crop='UNKNOWN'),observation(),(1,1),[[1,1]],CROPS)
    def test_empty_farm(self):
        o=observation();o['farms'][0]['tiles'][1][1]=None;rows,s=extract(o,CROPS);self.assertEqual(rows,[]);self.assertEqual(s['crop_count'],0)
    def test_all_paths_against_stepwise_adapter(self):
        for crop,p in CROPS.items():
            for day in (20,27):
                for age in (p['first_yield_day'],p['max_yield_day']+1):
                    for hour in (0,21,22):
                        for u in (0,1,p['max_yield']):
                            t=tile(crop=crop,planted_day=day-age,yield_units=u,max_lifespan_step=-1 if p['ongoing'] else (day-age+p['max_yield_day']+1)*24,fertilized_until_day=day)
                            for w,h in ((False,False),(True,False),(False,True),(True,True)):
                                with self.subTest(crop=crop,day=day,age=age,hour=hour,u=u,w=w,h=h):
                                    self.assertEqual(conditional_path(t,observation(day,hour),CROPS,w,h),component_path(t,day,hour,CROPS,w,h))
