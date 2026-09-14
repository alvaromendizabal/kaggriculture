from copy import deepcopy
from dataclasses import replace
import random,unittest
from unittest.mock import patch
from helpers import Route,Task,r,pas,brute_assign,routing_fixture,observation
from route_features import retain_original,enumerate_routes,complementary_menu,select_plan,FIELDS

class FeatureTests(unittest.TestCase):
    def test_original_sort(self):
        self.assertEqual(retain_original([r('A',30),r('B',50)],pas())[0].resources,frozenset(['B']))
    def test_pass_is_appended(self):self.assertEqual(retain_original([],pas()),[pas()])
    def test_direct_deposit_protected(self):
        rows=[r(str(i),100+i) for i in range(10)]+[r('',9,'DROP')]
        menu=retain_original(rows,pas());self.assertEqual(len(menu),9);self.assertIn(rows[-1],menu)
    def test_direct_does_not_add_ninth_active(self):
        menu=retain_original([r(str(i),200-i) for i in range(10)]+[r('',5,'DROP')],pas())
        self.assertEqual(sum(bool(r.actions) for r in menu),8)
    def test_invalid_limit(self):
        with self.assertRaises(ValueError):retain_original([],pas(),1)
    def test_opportunity_regret(self):
        pools=[[r('A',100),r('B',80)],[r('A',100)]];menus=[retain_original(p,pas()) for p in pools]
        inc,_=brute_assign(menus,100)
        _,rows=complementary_menu(pools,menus,inc)
        a=next(x for x in rows if x['worker']==0 and x['resource_signature']=='A')
        b=next(x for x in rows if x['worker']==0 and x['resource_signature']=='B')
        self.assertEqual(a['route.opportunity_cost_sum'],92)
        self.assertEqual(b['route.opportunity_cost_sum'],0)
    def test_complementary_alternative_admitted(self):
        # Eight redundant high-valued A routes hide a B route from the flexible worker.
        pool0=[r('A',100-i,'NORTH',work=1+i) for i in range(8)]+[r('B',30,'SOUTH')]
        pool1=[r('A',100)]
        pools=[pool0,pool1];menus=[retain_original(p,pas()) for p in pools];inc,base=brute_assign(menus,100)
        new,rows=complementary_menu(pools,menus,inc)
        choice,score=brute_assign(new,100)
        self.assertGreater(score['joint_utility'],base['joint_utility'])
        self.assertIn(pool0[-1],new[0])
    def test_schema(self):
        p=[[r()]];m=[retain_original(p[0],pas())];new,rows=complementary_menu(p,m,[p[0][0]])
        self.assertEqual({k.removeprefix('route.') for k in rows[0] if k.startswith('route.')},set(FIELDS))
    def test_no_mutation(self):
        p=[[r()],[r('B')]];m=[retain_original(x,pas()) for x in p];before=deepcopy((p,m))
        complementary_menu(p,m,[p[0][0],p[1][0]]);self.assertEqual((p,m),before)
    def test_missing_pass(self):
        with self.assertRaises(ValueError):complementary_menu([[r()]],[[r()]],[r()])
    def test_misaligned(self):
        with self.assertRaises(ValueError):complementary_menu([[r()]],[],[])
    def test_invalid_incumbent(self):
        with self.assertRaises(ValueError):complementary_menu([[r()]],[[r(),pas()]],[r('B')])
    def test_pass_incumbent_preserved(self):
        m,rows=complementary_menu([[r()]],[retain_original([r()],pas())],[pas()]);self.assertIn(pas(),m[0])
    def test_budget_matches_original(self):
        obs=observation(step=718,carried=2);p,m,meta=enumerate_routes(obs,routing_fixture())
        self.assertEqual(p[0][0].actions,(('DROP',),));self.assertEqual(meta['budget'],1)
    def test_missed_deadline(self):
        obs=observation(step=718,carried=2);obs['farms'][0]['farmer']=[0,0]
        p,m,meta=enumerate_routes(obs,routing_fixture());self.assertEqual(p,[[]])
    def test_shed_room(self):
        obs=observation(carried=2);obs['private']['shed']['WHEAT']=99
        p,_,_=enumerate_routes(obs,routing_fixture());self.assertFalse(p[0])
    def test_non_product_not_deposited(self):
        obs=observation(carried=2);obs['private']['inventories'][0]['GOOSE']=1
        p,_,_=enumerate_routes(obs,routing_fixture());self.assertFalse(p[0])
    def test_worker_alignment(self):
        obs=observation();obs['private']['inventories'].append({})
        with self.assertRaises(ValueError):enumerate_routes(obs,routing_fixture())
    def test_workforce_reject_not_truncate(self):
        with self.assertRaises(ValueError):enumerate_routes(observation(hands=4),routing_fixture())
    def test_opponent_workforce_also_checked(self):
        obs=observation();obs['farms'][1]['hands']=[[4,4]]*4
        with self.assertRaises(ValueError):enumerate_routes(obs,routing_fixture())
    def test_no_preterminal_study(self):
        with self.assertRaises(ValueError):enumerate_routes(observation(step=695),routing_fixture())
    def test_generation_safety_cap_not_silent_pruning(self):
        tasks=[Task((i,0,'H'),(0,0),(('HARVEST',),),'WHEAT',1) for i in range(200)]
        with self.assertRaises(ValueError):enumerate_routes(observation(),routing_fixture(tasks))
    def test_same_resource_never_collected_twice(self):
        tasks=[Task((1,1,'H'),(4,4),(('HARVEST',),),'WHEAT',1),Task((1,1,'H'),(4,4),(('WATER',),('HARVEST',)),'WHEAT',2)]
        p,_,_=enumerate_routes(observation(),routing_fixture(tasks));self.assertTrue(all(len(x.resources)<=1 for x in p[0]))
    def test_two_tasks_and_routes_present(self):
        tasks=[Task((i,4,'H'),(i,4),(('HARVEST',),),'WHEAT',1) for i in (3,4)]
        p,_,_=enumerate_routes(observation(),routing_fixture(tasks));self.assertTrue(any(len(x.resources)==2 for x in p[0]))
    def test_enumeration_no_mutation(self):
        obs=observation(carried=4);before=deepcopy(obs);enumerate_routes(obs,routing_fixture());self.assertEqual(obs,before)
    def test_arbitrary_feasible_incumbent_never_lost(self):
        rng=random.Random(431)
        for workers in (1,2,3,4):
            for trial in range(12):
                pools=[[r(str(rng.randrange(4)),rng.randrange(10,150),str(i),work=1+rng.randrange(3)) for i in range(12)] for _ in range(workers)]
                menus=[retain_original(p,pas()) for p in pools];inc,before=brute_assign(menus,3)
                new,_=complementary_menu(pools,menus,inc);_,after=brute_assign(new,3)
                self.assertTrue(all(i in m for i,m in zip(inc,new)))
                self.assertTrue(all(len(m)<=9 for m in new))
                self.assertGreaterEqual((after['joint_utility'],-after['joint_work']),(before['joint_utility'],-before['joint_work']))
    def test_equal_static_key_keeps_original_commands(self):
        rt=routing_fixture();obs=observation(carried=2)
        selected,d,*_=select_plan(obs,rt,brute_assign)
        self.assertFalse(d['farm_commands_changed']);self.assertFalse(d['static_key_improved'])
    def test_control_never_changes_commands(self):
        tasks=[Task((i,4,'H'),(i,4),(('HARVEST',),),'WHEAT',1) for i in (1,2,3,4)]
        chosen,d,*_=select_plan(observation(hands=2),routing_fixture(tasks),brute_assign,'control')
        self.assertFalse(d['farm_commands_changed'])
    def test_unsupported_mode(self):
        with self.assertRaises(ValueError):select_plan(observation(),routing_fixture(),brute_assign,'bad')
