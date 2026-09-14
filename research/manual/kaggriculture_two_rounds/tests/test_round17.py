import unittest,math
from copy import deepcopy
import arrival_features as f
from feature_common import decay_count,decay_tile
from mechanics import validate
from tests.fixtures import obs,tile,desc,GAME
class ArrivalTests(unittest.TestCase):
    def test_schema(self):self.assertEqual(len(desc(f,obs())),32)
    def test_summaries(self):self.assertEqual(len(f.extract(obs(),GAME)[1]),12)
    def test_no_travel_no_loss(self):self.assertEqual(desc(f,obs(expiry=244))['lost_units_on_route'],0)
    def test_loss_at_first_step(self):self.assertEqual(desc(f,obs(travel=1,expiry=244))['lost_units_on_route'],1)
    def test_parity_even(self):self.assertEqual(decay_count(tile(obs(expiry=244)),244,248),2)
    def test_parity_odd(self):self.assertEqual(decay_count(tile(obs(expiry=245)),244,248),2)
    def test_arrival_event_not_included(self):self.assertEqual(desc(f,obs(travel=1,expiry=245))['units_at_arrival'],4)
    def test_unexpired(self):self.assertEqual(desc(f,obs(travel=4,expiry=300))['units_at_arrival'],4)
    def test_no_expiry(self):self.assertEqual(desc(f,obs(travel=4))['units_at_arrival'],4)
    def test_cross_night_mask(self):self.assertEqual(desc(f,obs(hour=23,travel=1))['same_day_arrival'],0)
    def test_cross_night_preserves_value(self):self.assertEqual(desc(f,obs(hour=23,travel=1,expiry=0))['arrival_quote_value'],200)
    def test_zero_arrival(self):self.assertEqual(desc(f,obs(units=1,travel=4,expiry=244))['units_at_arrival'],0)
    def test_immutable(self):o=obs();b=deepcopy(o);desc(f,o);self.assertEqual(o,b)
    def test_no_future_metadata(self):o=obs();a=desc(f,o);o.update(seed=4,reward=1e9,future_actions=['DIG']);self.assertEqual(a,desc(f,o))
    def test_opponent_private_not_input(self):o=obs();a=desc(f,o);o['farms'][1]['private']={'shed':{'WHEAT':99}};self.assertEqual(a,desc(f,o))
    def test_seat_symmetry(self):o=obs();a=desc(f,o);o['farms'].reverse();o['player']=1;self.assertEqual(a,desc(f,o))
    def test_worker_includes_extra(self):o=obs();o['farms'][0]['hands']=[[4,4]]*12;o['private']['inventories']=[{}]*13;self.assertEqual(len(f.extract(o,GAME)[0]),13)
    def test_empty_table(self):o=obs(units=0);r,s=f.extract(o,GAME);self.assertEqual(r,[]);self.assertEqual(s['task_rows'],0)
    def test_immature_excluded(self):o=obs();tile(o)['planted_day']=10;self.assertEqual(f.extract(o,GAME)[0],[])
    def test_negative_slack_logged(self):r=desc(f,obs(day=29,hour=22,travel=4));self.assertLess(r['sale_slack_to_terminal'],0)
    def test_last_callback_at_shed(self):r=desc(f,obs(day=29,hour=22));self.assertEqual(r['delivery_within_season'],0)
    def test_decaying_to_weed(self):o=obs(units=1,expiry=244);self.assertEqual(decay_tile(tile(o),244,245),{'kind':'WEED'})
    def test_price_linear_scaling(self):o=obs(travel=1,expiry=244);a=desc(f,o);o['market']['prices']['TOMATO']*=2;self.assertEqual(desc(f,o)['lost_quote_value'],2*a['lost_quote_value'])
    def test_relative_loss(self):self.assertEqual(desc(f,obs(travel=1,expiry=244))['relative_value_reduction'],.25)
    def test_finite(self):self.assertTrue(all(math.isfinite(x) for x in desc(f,obs()).values()))
    def test_summary_unique_not_worker_sum(self):o=obs();o['farms'][0]['hands']=[[3,4]];o['private']['inventories'].append({});self.assertEqual(f.extract(o,GAME)[1]['total_ready_units_unique'],4)
    def test_exact_available_count(self):self.assertEqual(f.extract(obs(),GAME)[1]['same_day_task_rows'],1)
    def test_snapshot_state_variation(self):a=f.extract(obs(),GAME)[1];b=f.extract(obs(travel=4,expiry=244),GAME)[1];self.assertNotEqual(a,b)
    def test_live_check_harness(self):self.assertEqual(validate(GAME,'17')['cases'],480)
    def test_every_crop(self):
        for c in GAME.CROPS:self.assertEqual(len(desc(f,obs(crop=c))),32)
