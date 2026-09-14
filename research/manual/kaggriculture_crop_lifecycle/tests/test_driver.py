"""Complete file/checkpoint orchestration on a TOY engine, never real game scores."""
from pathlib import Path
from types import SimpleNamespace,ModuleType
from unittest.mock import patch
import tempfile,unittest,pandas as pd
import run_lifecycle as run
from research_io import write,sha
from helpers import ToyEnv,payload,GAME,toy_factory
class ToyActor:
    def __init__(self,game,mode,source_arm='coordinated'):self.mode=mode
    def prime_recorded_clock(self,*a):pass
    def __call__(self,o):return toy_factory(None,self.mode,o['player'],None)[0](o)
class DriverTests(unittest.TestCase):
    def test_all_three_branches_and_reuse(self):
        from lifecycle_experiment import rollout
        data=payload();keys=[dict(seed=s,seat=p,opponent='livestock_fertilizer',arm='coordinated') for s,p in [(1601,0),(1601,1),(1602,0)]]
        jobs=[dict(**k,sha256=str(i),path='unused') for i,k in enumerate(keys)]
        env=SimpleNamespace(game=GAME,make_environment=lambda seed:ToyEnv())
        module=ModuleType('kaggriculture_terminal.feed_policy');module.CROP_LAYOUT={}
        parent=ModuleType('kaggriculture_terminal');parent.feed_policy=module
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);out=home/'outputs';(home/'kaggriculture_sale_timing/outputs').mkdir(parents=True)
            pd.DataFrame([dict(**k,coins_guarded=3000.,opponent_coins_guarded=3000.) for k in keys]).to_csv(home/'kaggriculture_sale_timing/outputs/final_comparisons.csv',index=False)
            with patch.dict('sys.modules',{'kaggriculture_terminal':parent,'kaggriculture_terminal.feed_policy':module}),patch.object(run,'OUT',out),patch.object(run,'preflight',return_value=(home,env,'toy-fp')),patch.object(run,'test_stage',return_value={'tests':0,'scope':'toy-only'}),patch.object(run,'source_jobs',return_value=({},jobs)),patch.object(run,'load_source',side_effect=lambda r,p,j:(data,{k:j[k] for k in run.KEYS})),patch('lifecycle_policy.LifecyclePolicy',ToyActor),patch('mechanics.validate',return_value={'calendar_cases':0,'dig_replant_cases':0}),patch.object(run,'log'),patch.object(run,'emit'),patch('lifecycle_experiment.rollout',side_effect=lambda *a,**kw:rollout(*a,**kw,actor_factory=toy_factory)):
                run.screen(home);r=run.read(out/'screen/report.json')
                self.assertEqual((r['observations'],r['action_changes']),(372,3))
                write(out/'screen/status.json',{'status':'COMPLETED','report_sha256':sha(out/'screen/report.json')})
                run.pilot(home);p=run.read(out/'pilot/report.json')
                self.assertEqual(p['completed_branches'],3)
                self.assertEqual([x['coins_delta'] for x in p['paired_results']],[2,3])
                self.assertEqual(p['renew_minus_retire']['coins'],1)
                stamps={str(p):p.stat().st_mtime_ns for p in (out/'pilot/checkpoints').glob('*')}
                run.pilot(home)
                self.assertEqual(stamps,{str(p):p.stat().st_mtime_ns for p in (out/'pilot/checkpoints').glob('*')})
                self.assertEqual(run.read(out/'pilot/report.json')['new_suffix_transitions'],0)
    def test_responsive_opponent_toy(self):
        from lifecycle_experiment import rollout,paired
        data=payload();key=dict(seed=1601,seat=0,opponent='livestock_fertilizer',arm='coordinated')
        def factory(g,mode,seat,arm):
            c,r,n,_=toy_factory(g,mode,seat,arm)
            def enemy(o):
                a={'farmer':['PASS'],'hands':[],'market':[]}
                if o['step']==193 and o['farms'][0]['money']>3000:a['market']=[['TOY_CASH',1]]
                return a
            return c,r,n,enemy
        b=[rollout(data,key,m,GAME,lambda s:ToyEnv(),{'coins_guarded':3000.,'opponent_coins_guarded':3000.},lambda *a:None,lambda *a,**kw:None,factory) for m in ('control','renew')]
        self.assertEqual(paired(*b)['opponent_coins_delta'],1)
