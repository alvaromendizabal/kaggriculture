from copy import deepcopy
from pathlib import Path
import ast,gzip,json,tempfile,unittest
from unittest.mock import patch
from types import SimpleNamespace
import factorial_analysis as fa
from factorial_io import read,digest,save_cache,load_cache,inside
from factorial_policy import allowed,transform_call
from joint_features import extract,FIELDS
from tests.fixtures import observation,plant,GAME,CROPS,ToyEnv,payload
from factorial_experiment import observations,rollout,screen_block,identical_branch,measure,indexed_source
BASE=Path(__file__).resolve().parents[1]


def known():
    return fa.historical_branches(BASE/'reference/notebook15',read(BASE/'reference/input_hashes.json'))[0]


def complete():
    b=known();b['clear_only']=deepcopy(b['control']);b['clear_only']['mode']='clear_only'
    b['clear_only']['metrics']['coins']+=100;b['clear_only']['metrics']['coin_margin']+=100
    return b


class EvidenceTests(unittest.TestCase):
    def test_uploaded_checkpoints(self):
        b=known();self.assertEqual(b['retire']['metrics']['coins'],41510);self.assertEqual(b['renew']['metrics']['coin_margin'],1812)
    def test_mixed_result_not_silently_relabelled(self):
        b=known();r=fa.assess(b['control'],b['renew']);self.assertEqual(r['competitive_interpretation'],'SAME_MATCH_HIGHER_MARGIN');self.assertEqual(r['existing_conservative_gate'],'STOP_NEGATIVE_ENDPOINT')
    def test_negative_match_overrides_margin_language(self):
        b=complete();c=b['clear_only'];c['metrics']['local_match_score']=0
        self.assertEqual(fa.assess(b['control'],c)['competitive_interpretation'],'LOCAL_MATCH_REGRESSION')
    def test_exact_factorial_math(self):
        r=next(r for r in fa.full_factorial(complete()) if r['metric']=='coins')
        self.assertEqual(r['clearing_effect_normal_water'],100);self.assertEqual(r['clearing_effect_retired_water'],1941);self.assertEqual(r['difference_in_differences'],1841)
    def test_missing_cell_not_imputed(self):
        with self.assertRaises(ValueError):fa.full_factorial(known())
    def test_no_input_mutation(self):
        b=complete();h=digest(b);fa.full_factorial(b);self.assertEqual(h,digest(b))
    def test_nonfinite_rejected(self):
        b=complete();b['clear_only']['metrics']['coins']=float('nan')
        with self.assertRaises(ValueError):fa.full_factorial(b)
    def test_wrong_seed_rejected(self):
        b=complete();b['clear_only']['key']['seed']=7
        with self.assertRaises(ValueError):fa.full_factorial(b)
    def test_initial_state_mismatch_rejected(self):
        b=complete();b['clear_only']['initial_sha256']='bad'
        with self.assertRaises(ValueError):fa.full_factorial(b)
    def test_checkpoint_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.gz';save_cache(p,'fp',{'ok':1});self.assertEqual(load_cache(p,'fp'),{'ok':1})
    def test_checkpoint_fingerprint_guard(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.gz';save_cache(p,'fp',{'ok':1})
            with self.assertRaises(ValueError):load_cache(p,'changed')
    def test_no_checkpoint_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.gz';save_cache(p,'fp',{'ok':1})
            with self.assertRaises(ValueError):save_cache(p,'fp',{'ok':2})
    def test_escape_path_rejected(self):
        with self.assertRaises(ValueError):inside(BASE,'../../etc/passwd')
    def test_checkpoint_tamper_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.gz';save_cache(p,'fp',{'ok':1});doc=json.loads(gzip.decompress(p.read_bytes()));doc['payload']['ok']=3;p.write_bytes(gzip.compress(json.dumps(doc).encode()))
            with self.assertRaises(ValueError):load_cache(p,'fp')


SOURCE='''def __call__(self, obs):
    for target, crop in CROP_LAYOUT.items():
        tile = obs['tile']
        if tile is None:
            pass
        elif isinstance(tile, dict) and tile.get("kind") == "WEED":
            return 'DIG'
    if not tile["watered_today"]:
        return 'WATER'
    return 'PASS'
'''


class PolicyTests(unittest.TestCase):
    def test_water_expression_unchanged(self):
        tree=transform_call(SOURCE);water=ast.dump(ast.parse('not tile["watered_today"]',mode='eval').body,include_attributes=False)
        self.assertEqual(sum(ast.dump(n.test,include_attributes=False)==water for n in ast.walk(tree) if isinstance(n,ast.If)),1)
    def test_clear_added_once(self):
        tree=transform_call(SOURCE);self.assertEqual(sum(isinstance(n,ast.Name) and n.id=='__clear_spent' for n in ast.walk(tree)),1)
    def test_no_clearing_site_fails(self):
        with self.assertRaises(ValueError):transform_call('def f(self,x): return x')
    def test_multiple_clearing_sites_fail(self):
        with self.assertRaises(ValueError):transform_call(SOURCE+'\n'+SOURCE.replace('__call__','other'))
    def test_null_retains_water(self):
        ns={'CROP_LAYOUT':{(4,4):'TOMATO'},'__clear_spent':lambda t,o:False};exec(compile(transform_call(SOURCE),'<test>','exec'),ns)
        self.assertEqual(ns['__call__'](None,{'tile':plant('TOMATO',0,0)}),'WATER')
    def test_clearing_transformation_executes(self):
        ns={'CROP_LAYOUT':{(4,4):'TOMATO'},'__clear_spent':lambda t,o:True};exec(compile(transform_call(SOURCE),'<test>','exec'),ns)
        self.assertEqual(ns['__call__'](None,{'tile':plant('TOMATO',0,0)}),'DIG')
    def test_null_mode_never_enables_clear(self):
        o=observation(20,0);self.assertFalse(allowed(plant('TOMATO',0,0),o,CROPS,'null'))
    def test_spent_empty_clears(self):
        self.assertTrue(allowed(plant('TOMATO',0,0),observation(20,0),CROPS,'clear_only'))
    def test_held_goods_protected(self):
        self.assertFalse(allowed(plant('TOMATO',0,1),observation(20,0),CROPS,'clear_only'))
    def test_future_production_protected(self):
        self.assertFalse(allowed(plant('TOMATO',15,0),observation(20,0),CROPS,'clear_only'))
    def test_outside_window(self):
        self.assertFalse(allowed(plant('TOMATO',0,0),observation(28,0),CROPS,'clear_only'))
    def test_bad_mode(self):
        with self.assertRaises(ValueError):allowed(plant('TOMATO',0,0),observation(20,0),CROPS,'retire')


class FeatureTests(unittest.TestCase):
    def test_shape_and_overlap(self):
        o=observation(12,0,plant('TOMATO',0,0));f=extract(o,GAME,{(4,4):'TOMATO'});self.assertEqual(set(f),set(FIELDS));self.assertEqual(f['clear_water_overlap_fraction'],1);self.assertEqual(f['min_clear_plant_water_actions'],3)
    def test_watered_overlap(self):
        o=observation(12,0,plant('TOMATO',0,0,watered=True));f=extract(o,GAME,{(4,4):'TOMATO'});self.assertEqual(f['clearable_watered_plots'],1);self.assertEqual(f['clear_water_overlap_fraction'],0)
    def test_seed_availability(self):
        o=observation(12,0,plant('TOMATO',0,0));o['private']['seeds']['TOMATO']=1;self.assertEqual(extract(o,GAME,{(4,4):'TOMATO'})['clearable_seed_ready_plots'],1)
    def test_expired_replant_window(self):
        o=observation(27,0,plant('TOMATO',0,0));self.assertEqual(extract(o,GAME,{(4,4):'TOMATO'})['clear_eligible_spent_plots'],0)
    def test_more_than_three_workers_not_truncated_in_features(self):
        o=observation(12,0);o['farms'][0]['hands']=[[4,4]]*12;self.assertEqual(extract(o,GAME,{})['current_workers'],13)
    def test_feature_ignores_future_and_rival_private(self):
        o=observation(12,0,plant('TOMATO',0,0));a=extract(o,GAME,{(4,4):'TOMATO'});o['reward']=99999;o['seed']=4;o['future_shop']='X';o['farms'][1]={'hidden':object()};self.assertEqual(a,extract(o,GAME,{(4,4):'TOMATO'}))
    def test_feature_immutable(self):
        o=observation(12,0,plant('TOMATO',0,0));h=digest(o);extract(o,GAME,{(4,4):'TOMATO'});self.assertEqual(h,digest(o))
    def test_bad_clock(self):
        o=observation(12,0);o['step']=1
        with self.assertRaises(ValueError):extract(o,GAME,{})
    def test_bad_board(self):
        o=observation(12,0);o['farms'][0]['tiles']=[]
        with self.assertRaises(ValueError):extract(o,GAME,{})
    def test_official_calendar_excerpt(self):
        from tests import official_refresh_excerpt as excerpt
        from mechanics import core_checks
        self.assertEqual(len(core_checks(excerpt)),380)


def actions(obs):return {'farmer':['PASS'],'hands':[],'market':[]}

def toy_actors(game,key,start):
    def candidate(obs):
        a=actions(obs)
        if obs['step']==192:a['market']=[['TOY_CASH',2]]
        return a
    def rival(obs):
        a=actions(obs)
        if obs['farms'][key['seat']]['money']>3000 and obs['step']==193:a['market']=[['TOY_CASH',1]]
        return a
    return candidate,actions,actions,rival


def control_fixture(src):
    env=ToyEnv()
    for _ in range(192):env.step([actions(None),actions(None)])
    initial=digest(observations(env));trace=[]
    for step in range(192,719):
        trace.append({'step':step,'mode':'control','action':actions(None),'own_cash_before':3000.,'own_cash':3000.,'opponent_cash':3000.,'own_shed_before':{'WHEAT':0},'candidate_callback_ms':0.,'water_commands':0})
    return {'mode':'control','key':{'seed':1601,'seat':0,'arm':'coordinated','opponent':'livestock_fertilizer'},'initial_sha256':initial,'trace':trace,'metrics':{'coins':3000.,'opponent_coins':3000.,'coin_margin':0.,'local_match_score':.5,'residual_product_units':0},'suffix_transitions':527,'null_action_checks':527}


class DriverTests(unittest.TestCase):
    def test_one_new_branch_responsive_opponent(self):
        p=payload();c=control_fixture(p)
        b=rollout(p,c['key'],c,GAME,lambda _:ToyEnv(),{},lambda *a:None,lambda *a,**k:None,actor_factory=toy_actors)
        self.assertEqual(b['metrics']['coins'],3002);self.assertEqual(b['metrics']['opponent_coins'],3001);self.assertEqual(b['new_transitions'],719)
    def test_screen_detects_change(self):
        p=payload();c=control_fixture(p);r=screen_block(p,c['key'],c,GAME,{},192,193,lambda *a:None,actor_factory=toy_actors);self.assertEqual(sum(t['changed'] for t in r),1)
    def test_no_activation_identity_proof(self):
        p=payload();c=control_fixture(p);r=[{'step':t['step'],'changed':False,'action':t['action'],'reference_action':t['action']} for t in c['trace']]
        out=identical_branch(c,r);self.assertEqual(out['metrics'],c['metrics']);self.assertEqual(out['new_transitions'],0)
    def test_sparse_identity_proof_rejected(self):
        p=payload();c=control_fixture(p)
        with self.assertRaises(ValueError):identical_branch(c,[])
    def test_changed_action_cannot_claim_identity(self):
        p=payload();c=control_fixture(p);r=[{'step':t['step'],'changed':False,'action':t['action'],'reference_action':t['action']} for t in c['trace']];r[0]['changed']=True
        with self.assertRaises(ValueError):identical_branch(c,r)
    def test_duplicate_source_rejected(self):
        p=payload();p['records'].append(p['records'][0])
        with self.assertRaises(ValueError):indexed_source(p)
    def test_input_mutating_actor_rejected(self):
        def actor(o):o['day']=5;return actions(o)
        with self.assertRaises(ValueError):measure(actor,observation(12,0),'test',lambda *a:None)
    def test_actual_clock_latency_guard(self):
        with patch('factorial_experiment.time.perf_counter',side_effect=[10.,10.501]):
            with self.assertRaises(RuntimeError):measure(actions,observation(12,0),'test',lambda *a:None)
    def test_wrong_initial_state(self):
        p=payload();c=control_fixture(p);c['initial_sha256']='bad'
        with self.assertRaises(ValueError):rollout(p,c['key'],c,GAME,lambda _:ToyEnv(),{},lambda *a:None,lambda *a,**k:None,actor_factory=toy_actors)
    def test_bad_null_actor_stops(self):
        def factory(g,k,s):
            a=toy_actors(g,k,s)
            return a[0],a[1],lambda o:{'farmer':['WATER'],'hands':[],'market':[]},a[3]
        p=payload();c=control_fixture(p)
        with self.assertRaises(ValueError):screen_block(p,c['key'],c,GAME,{},192,192,lambda *a:None,actor_factory=factory)
