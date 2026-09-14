from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from route_experiment import measure,paired,decision,rollout
from helpers import observation


def pair_fixture(delta=0,source_arm='coordinated',changes=1):
    key={'seed':1601,'seat':0,'arm':source_arm,'opponent':'livestock_fertilizer'}
    common={'key':key,'initial_state_sha256':'a','final_state_sha256':'b','transitions':23,'source_checks':23,
            'candidate_actions':[{'farmer':['PASS']}]*23,'opponent_actions':[{'farmer':['PASS']}]*23,
            'metrics':{'coins':100.,'opponent_coins':80.,'coin_margin':20.,'local_match_score':1.,'residual_product_units':0},
            'trace':[{'same_state_farm_changed':False}]*23}
    a=deepcopy(common);b=deepcopy(common);a['mode']='control';b['mode']='opportunity'
    b['metrics']['coins']+=delta;b['metrics']['coin_margin']+=delta
    b['trace']=[{'same_state_farm_changed':i<changes} for i in range(23)]
    if delta:b['final_state_sha256']='c'
    return a,b

class ExperimentTests(unittest.TestCase):
    def test_positive(self):self.assertEqual(decision([paired(*pair_fixture(2))]),'PROMISING_SINGLE_DEVELOPMENT_PAIR_NOT_VALIDATED')
    def test_negative(self):self.assertEqual(decision([paired(*pair_fixture(-1))]),'STOP_NEGATIVE_ENDPOINT')
    def test_no_activation(self):self.assertEqual(decision([paired(*pair_fixture(0,changes=0))]),'STOP_NO_TRAJECTORY_ACTIVATION')
    def test_no_benefit(self):self.assertEqual(decision([paired(*pair_fixture(0))]),'STOP_NO_ENDPOINT_BENEFIT')
    def test_incomplete(self):self.assertEqual(decision([]),'INCOMPLETE_NO_PRIMARY_RESULT')
    def test_negative_control_zero(self):self.assertEqual(paired(*pair_fixture(0,'sequential',0))['coins_delta'],0)
    def test_negative_control_failure(self):
        with self.assertRaises(ValueError):paired(*pair_fixture(1,'sequential',0))
    def test_unpaired(self):
        a,b=pair_fixture();b['initial_state_sha256']='different'
        with self.assertRaises(ValueError):paired(a,b)
    def test_partial_not_scored(self):
        a,b=pair_fixture();b['transitions']=22
        with self.assertRaises(ValueError):paired(a,b)
    def test_missing_control_reproduction(self):
        a,b=pair_fixture();a['source_checks']=0
        with self.assertRaises(ValueError):paired(a,b)
    def test_outcomes_separate_from_agent(self):
        obs=observation();seen=[]
        measure(lambda o:seen.append(set(o)) or {'farmer':['PASS']},obs,'test',lambda *x:None)
        self.assertNotIn('reward',seen[0]);self.assertNotIn('seed',seen[0])
    def test_mutation_rejected(self):
        def actor(o):o['day']=0;return {}
        with self.assertRaises(ValueError):measure(actor,observation(),'actor',lambda *a:None)
    def test_latency_rejection_saved_first(self):
        logged=[]
        with patch('route_experiment.time.perf_counter',side_effect=[0.,.6]):
            with self.assertRaises(RuntimeError):measure(lambda o:{},observation(),'slow',lambda *a:logged.append(a))
        self.assertEqual(len(logged),1);self.assertEqual(logged[0][1]['callback_ms'],600.)
    def test_nonfinite_latency(self):
        with patch('route_experiment.time.perf_counter',side_effect=[0.,float('nan')]):
            with self.assertRaises(RuntimeError):measure(lambda o:{},observation(),'nan',lambda *x:None)
    def test_wrong_branch(self):
        with self.assertRaises(ValueError):rollout({}, {'opponent':'bad'},'bad',None,{},lambda *x:None,{})


def toy_engine(seat=0):
    """Deliberately synthetic cash dynamics for exercising the trajectory driver."""
    obs=observation();obs['player']=seat
    obs['farms'][seat]['money']=100.;obs['farms'][1-seat]['money']=80.
    other=deepcopy(obs);other['player']=1-seat
    private_keys=set(obs['private'])
    pas={'farmer':['PASS'],'hands':[],'market':[]}
    records={}
    for step in range(696,719):
        for p in (0,1):
            o=deepcopy(obs if p==seat else other);o['step']=step;o['hour']=step%24
            records[step,p]={'observation':o,'action':deepcopy(pas),'player':p}
    def legal(o):
        o={k:deepcopy(o[k]) for k in ('player','day','hour','farms','private','market','town')}
        o['step']=o['day']*24+o['hour'];return o
    def transition(own,rival,a,b,game):
        assert set(own['private'])==private_keys and set(rival['private'])==private_keys
        farms=deepcopy(own['farms']);p=own['player']
        farms[p]['money']+=int(a['farmer']==['GAIN'])
        farms[1-p]['money']+=2*int(b['farmer']==['BOOST'])
        step=own['step']+1;ret=[None,None]
        for old in (own,rival):
            state=legal(old);state['farms']=deepcopy(farms);state['step']=step;state['day']=step//24;state['hour']=step%24
            state['status']='DONE' if step==719 else 'ACTIVE';state['reward']=farms[old['player']]['money'] if step==719 else 0.
            ret[old['player']]=state
        return ret
    def metrics(result,p,products):
        a=result[p]['reward'];b=result[1-p]['reward']
        return {'coins':a,'opponent_coins':b,'coin_margin':a-b,'local_match_score':float(a>b)+.5*float(a==b),'residual_product_units':0}
    def assert_source(result,nxt,rewards,step):
        if step<718:
            assert all(result[p]['farms']==nxt[p]['observation']['farms'] for p in (0,1))
    class Actor:
        def __init__(self,treatment=False,opponent=False):self.treatment=treatment;self.opponent=opponent;self.last_diagnostics={};self.last=695
        def __call__(self,o):
            assert o['step']==self.last+1;self.last=o['step']
            assert 'reward' not in o and 'seed' not in o
            result=deepcopy(pas)
            if self.treatment:result['farmer']=['GAIN']
            if self.opponent and o['farms'][1-o['player']]['money']>102:result['farmer']=['BOOST']
            self.last_diagnostics={'active':True,'same_state_control_action':deepcopy(pas),
                                   'routing':{'static_utility_delta':1. if self.treatment else 0.,'static_key_improved':self.treatment}}
            return result
    def factory(arm,mode,p):return Actor(arm=='coordinated' and mode=='opportunity'),Actor(opponent=True),Actor()
    mods={'continuation':SimpleNamespace(index_episode=lambda p:p['records'],legal_observation=legal,
            project_next=lambda r:[legal(x) for x in r],terminal_metrics=metrics),
          'run_cash':SimpleNamespace(isolated_transition=transition,assert_source_transition=assert_source)}
    expected={k+'_guarded':v for k,v in {'coins':100.,'opponent_coins':80.,'coin_margin':20.,'local_match_score':1.,'residual_product_units':0}.items()}
    return {'records':records,'rewards':[100.,80.] if seat==0 else [80.,100.]},mods,expected,factory

class DriverTests(unittest.TestCase):
    def test_live_state_propagation_both_seats(self):
        for seat in (0,1):
            payload,mods,expected,factory=toy_engine(seat)
            key={'seed':1601,'seat':seat,'opponent':'livestock_fertilizer','arm':'coordinated'}
            a=rollout(payload,key,'control',SimpleNamespace(PRODUCTS=['WHEAT']),mods,lambda *x:None,expected,factory)
            b=rollout(payload,key,'opportunity',SimpleNamespace(PRODUCTS=['WHEAT']),mods,lambda *x:None,expected,factory)
            self.assertEqual(b['metrics']['coins'],123.)
            self.assertEqual(b['trace'][0]['own_cash'],101.)
            self.assertEqual(b['trace'][1]['own_cash'],102.)
            self.assertGreater(paired(a,b)['opponent_action_changes'],0)
    def test_sequential_no_change(self):
        payload,mods,expected,factory=toy_engine()
        key={'seed':1601,'seat':0,'opponent':'livestock_fertilizer','arm':'sequential'}
        a=rollout(payload,key,'control',SimpleNamespace(PRODUCTS=[]),mods,lambda *x:None,expected,factory)
        b=rollout(payload,key,'opportunity',SimpleNamespace(PRODUCTS=[]),mods,lambda *x:None,expected,factory)
        self.assertEqual(paired(a,b)['coins_delta'],0)
    def test_control_wrong_expected_endpoint_rejected(self):
        payload,mods,expected,factory=toy_engine();expected['coins_guarded']=999
        key={'seed':1601,'seat':0,'opponent':'livestock_fertilizer','arm':'coordinated'}
        with self.assertRaises(ValueError):rollout(payload,key,'control',SimpleNamespace(PRODUCTS=[]),mods,lambda *x:None,expected,factory)
    def test_actor_error_not_swallowed(self):
        def bad(*x):raise RuntimeError('broken actor')
        payload,mods,expected,_=toy_engine();key={'seed':1601,'seat':0,'opponent':'livestock_fertilizer','arm':'coordinated'}
        with self.assertRaisesRegex(RuntimeError,'broken'):rollout(payload,key,'control',SimpleNamespace(PRODUCTS=[]),mods,lambda *x:None,expected,bad)
