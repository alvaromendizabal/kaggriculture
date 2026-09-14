import unittest,math
from copy import deepcopy
import headroom_features as f
from feature_common import refresh
from mechanics import validate,farm
from tests.fixtures import obs,tile,desc,GAME
class HeadroomTests(unittest.TestCase):
    def test_schema(self):self.assertEqual(len(desc(f,obs())),32)
    def test_summaries(self):self.assertEqual(len(f.extract(obs(),GAME)[1]),12)
    def test_full_cap_releases_base(self):self.assertEqual(desc(f,obs())['released_production_units'],1)
    def test_fertilized_releases_two(self):self.assertEqual(desc(f,obs(fert=True))['released_production_units'],2)
    def test_no_cap_loss(self):self.assertEqual(desc(f,obs(units=1))['released_production_units'],0)
    def test_partial_cap_loss(self):self.assertEqual(desc(f,obs(units=3,fert=True))['released_production_units'],1)
    def test_dry_death_no_gain(self):self.assertEqual(desc(f,obs(wet=False,streak=1))['released_production_units'],0)
    def test_fertilizer_requires_water(self):self.assertEqual(desc(f,obs(wet=False,fert=True))['released_production_units'],1)
    def test_dry_survival(self):self.assertEqual(desc(f,obs(wet=False,streak=0))['survives_hold'],1)
    def test_no_future_event(self):o=obs();tile(o)['planted_day']-=10;self.assertEqual(desc(f,o)['released_production_units'],0)
    def test_strawberry_due(self):self.assertEqual(desc(f,obs(crop='STRAWBERRY'))['released_production_units'],1)
    def test_strawberry_offday(self):o=obs(crop='STRAWBERRY');tile(o)['planted_day']+=1;self.assertEqual(desc(f,o)['released_production_units'],0)
    def test_nonrecurring_mask(self):self.assertEqual(desc(f,obs(crop='WHEAT'))['scenario_available'],0)
    def test_cross_midnight_mask(self):self.assertEqual(desc(f,obs(hour=23,travel=1))['scenario_available'],0)
    def test_no_refresh_at_season_end(self):self.assertEqual(desc(f,obs(day=29,hour=20))['scenario_available'],0)
    def test_hold_production(self):self.assertEqual(desc(f,obs(units=2))['produced_hold'],1)
    def test_harvest_production(self):self.assertEqual(desc(f,obs(units=4,fert=True))['produced_harvest'],2)
    def test_augmented_formula(self):r=desc(f,obs());self.assertEqual(r['augmented_harvest_value'],r['current_quote_value']+r['released_quote_value'])
    def test_immutable(self):o=obs();b=deepcopy(o);desc(f,o);self.assertEqual(o,b)
    def test_no_future_metadata(self):o=obs();a=desc(f,o);o.update(seed=8,reward=100,future_shops=['X']);self.assertEqual(a,desc(f,o))
    def test_opponent_private_not_input(self):o=obs();a=desc(f,o);o['farms'][1]['private']={'wheat':99};self.assertEqual(a,desc(f,o))
    def test_seat_symmetry(self):o=obs();a=desc(f,o);o['farms'].reverse();o['player']=1;self.assertEqual(a,desc(f,o))
    def test_worker_allocation_not_truncated(self):o=obs();o['farms'][0]['hands']=[[4,4]]*12;o['private']['inventories']=[{}]*13;self.assertEqual(len(f.extract(o,GAME)[0]),13)
    def test_zero_rows(self):self.assertEqual(f.extract(obs(units=0),GAME)[0],[])
    def test_no_stock_at_arrival(self):self.assertEqual(desc(f,obs(units=1,travel=4,expiry=244))['released_production_units'],0)
    def test_zero_life_harvest_not_magic(self):self.assertEqual(desc(f,obs(expiry=244))['released_production_units'],0)
    def test_feature_values_finite(self):self.assertTrue(all(math.isfinite(x) for x in desc(f,obs()).values()))
    def test_official_refresh_excerpt(self):
        o=obs(fert=True,units=2);a,_=refresh(tile(o),10,GAME.CROPS);ff=farm(tile(o));GAME._daily_refresh_plants(ff,10,24);self.assertEqual(a,ff['tiles'][4][4])
    def test_live_check_harness(self):self.assertEqual(validate(GAME,'18')['cases'],288)
    def test_every_crop(self):
        for c in GAME.CROPS:self.assertEqual(len(desc(f,obs(crop=c))),32)
