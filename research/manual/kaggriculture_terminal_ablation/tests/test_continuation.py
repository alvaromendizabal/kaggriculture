from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fixtures import GAME,observation,make_payload,factory,transition
import continuation as c
from terminal_context import extract
from run_cash import assert_source_transition

class ContinuationTests(unittest.TestCase):
    def run_branch(self,deposit=716,source='coordinated',seat=0,variant='control',emit=None,actors=None):
        p,k=make_payload(seat,source,deposit)
        return c.rollout(p,k,variant,GAME,transition,assert_source_transition,emit or (lambda *x:None),
                         actor_factory=actors or factory(deposit),context_extractor=extract)
    def test_23_control_steps_and_recorded_parity(self):
        r=self.run_branch();self.assertEqual(r['transitions'],23);self.assertEqual(r['control_recorded_transition_parity_checks'],23)
    def test_control_reproduces_both_seats(self):
        for s in (0,1):self.assertEqual(self.run_branch(seat=s)['metrics']['coins'],3020)
    def test_early_sale_is_not_a_terminal_gain(self):
        a=self.run_branch();b=self.run_branch(variant='aligned');r=c.pair_results(a,b)
        self.assertEqual(r['coins_delta'],0);self.assertGreater(r['same_state_market_changes'],0)
    def test_last_callback_stranding_does_improve_endpoint(self):
        r=c.pair_results(self.run_branch(718),self.run_branch(718,variant='aligned'))
        self.assertEqual(r['coins_delta'],20)
    def test_live_opponent_response_is_recomputed(self):
        a=self.run_branch();b=self.run_branch(variant='aligned');r=c.pair_results(a,b)
        self.assertGreater(r['opponent_action_changes_across_trajectories'],0)
    def test_sequential_negative_control_has_identical_path(self):
        a=self.run_branch(source='sequential');b=self.run_branch(source='sequential',variant='aligned')
        r=c.pair_results(a,b);self.assertEqual(r['role'],'negative_control');self.assertEqual(r['coins_delta'],0)
    def test_170_causal_descriptors(self):
        r=self.run_branch();self.assertEqual(len(r['features'][0])-2,170)
        self.assertNotIn('rewards',r['features'][0]);self.assertNotIn('coins_delta',r['features'][0])
    def test_metadata_not_passed_to_actor(self):
        # Candidate and Rival assert exact legal field set on every call.
        self.run_branch(variant='aligned')
    def test_source_not_mutated(self):
        p,k=make_payload();old=deepcopy(p)
        c.rollout(p,k,'aligned',GAME,transition,assert_source_transition,lambda *x:None,actor_factory=factory())
        self.assertEqual(p,old)
    def test_missing_record_rejected(self):
        p,k=make_payload();p['records'].pop()
        with self.assertRaises(ValueError):c.index_episode(p)
    def test_duplicate_record_rejected(self):
        p,k=make_payload();p['records'].append(p['records'][0])
        with self.assertRaises(ValueError):c.index_episode(p)
    def test_conflicting_clock_rejected(self):
        o=observation();o['step']=1
        with self.assertRaises(ValueError):c.legal_observation(o)
    def test_missing_step_derived_from_public_clock(self):
        o=observation();o.pop('step');self.assertEqual(c.legal_observation(o)['step'],696)
    def test_null_step_derived(self):
        o=observation();o['step']=None;self.assertEqual(c.legal_observation(o)['step'],696)
    def test_terminal_outcome_not_fed_back_to_policy(self):
        o=observation();o.update(reward=9999,seed=1601,status='ACTIVE',opponent_private={'x':9})
        self.assertEqual(set(c.legal_observation(o)),set(c.LEGAL))
    def test_state719_not_actionable(self):
        with self.assertRaises(ValueError):c.legal_observation(observation(step=719))
    def test_source_control_action_drift_rejected(self):
        p,k=make_payload();p['records'][0]['action']['farmer']=['EAST']
        with self.assertRaisesRegex(ValueError,'control action'):
            c.rollout(p,k,'control',GAME,transition,assert_source_transition,lambda *x:None,actor_factory=factory())
    def test_recorded_opponent_action_drift_rejected(self):
        p,k=make_payload();p['records'][1]['action']['farmer']=['EAST']
        with self.assertRaisesRegex(ValueError,'opponent action'):
            c.rollout(p,k,'control',GAME,transition,assert_source_transition,lambda *x:None,actor_factory=factory())
    def test_timing_saved_before_failure(self):
        events=[]
        with patch.object(c.time,'perf_counter',side_effect=[0.,.6,1.,1.001]):
            with self.assertRaisesRegex(RuntimeError,'500 ms'):self.run_branch(emit=lambda *x:events.append(x))
        self.assertEqual(events[0][0],'CALLBACK_MEASURED');self.assertEqual(events[0][1]['sample']['candidate_callback_ms'],600)
    def test_same_state_shadow_rejects_routing_change(self):
        def changed(source,variant,seat):
            cand,riv,shadow=factory()(source,variant,seat)
            if variant=='aligned':
                original=cand
                class Wrapper:
                    def __call__(self,obs):
                        action=original(obs);action['farmer']=['EAST'];self.last_diagnostics=original.last_diagnostics;return action
                cand=Wrapper()
            return cand,riv,shadow
        with self.assertRaisesRegex(ValueError,'attribution'):self.run_branch(variant='aligned',actors=changed)
    def test_pair_initial_state_mismatch_rejected(self):
        a=self.run_branch();b=deepcopy(a);b['variant']='aligned';b['initial_state_sha256']='bad'
        with self.assertRaises(ValueError):c.pair_results(a,b)
    def test_partial_branch_not_scored(self):
        a=self.run_branch();b=deepcopy(a);b['variant']='aligned';b['transitions']=22
        with self.assertRaises(ValueError):c.pair_results(a,b)
    def test_bad_negative_control_rejected(self):
        a=self.run_branch(source='sequential');b=deepcopy(a);b['variant']='aligned';b['metrics']['coins']+=1
        with self.assertRaisesRegex(ValueError,'negative control'):c.pair_results(a,b)
    def test_missing_done_rejected(self):
        with self.assertRaises(ValueError):c.terminal_metrics([{'status':'ACTIVE'}]*2,0,GAME.PRODUCTS)
    def test_win_draw_loss_score(self):
        self.assertEqual([c.local_match(x) for x in (1,0,-1)],[1,.5,0])
    def test_nonfinite_score_rejected(self):
        with self.assertRaises(ValueError):c.local_match(float('nan'))

class DecisionTests(unittest.TestCase):
    def row(self,**kw):return {'role':'primary_intervention','coins_delta':0,'coin_margin_delta':0,'local_match_score_delta':0,'same_state_market_changes':1,**kw}
    def test_no_terminal_benefit(self):self.assertEqual(c.decision([self.row()],True),'STOP_NO_TERMINAL_BENEFIT')
    def test_no_activation(self):self.assertEqual(c.decision([self.row(same_state_market_changes=0)],True),'STOP_NO_ACTIVATION')
    def test_negative_coins_stops(self):self.assertEqual(c.decision([self.row(coins_delta=-1)],False),'STOP_NEGATIVE_TERMINAL_EFFECT')
    def test_negative_margin_stops(self):self.assertEqual(c.decision([self.row(coin_margin_delta=-1)],True),'STOP_NEGATIVE_TERMINAL_EFFECT')
    def test_positive_requires_fresh_groups(self):self.assertEqual(c.decision([self.row(coins_delta=1)],True),'PROMISING_REQUIRES_FRESH_GROUPS_AND_DISTINCT_OPPONENTS')
    def test_incomplete_not_promoted(self):self.assertEqual(c.decision([self.row(coins_delta=1)],False),'INCOMPLETE_NO_PERFORMANCE_CONCLUSION')
