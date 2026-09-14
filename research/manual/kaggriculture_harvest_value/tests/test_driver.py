"""End-to-end stage orchestration on a named TOY evaluator, not game results."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from copy import deepcopy
import tempfile,unittest,pandas as pd
import run_harvest as runner
from research_io import write,sha
from helpers import ToyEnv,payload
from price_adapter import GAME

class ToyActor:
    def __init__(self,game,mode,source_arm='coordinated'):self.mode=mode
    def prime_recorded_clock(self,*a):pass
    def __call__(self,o):
        a={'farmer':['PASS'],'hands':[],'market':[]}
        if self.mode=='marginal' and o['step']==480:a['market']=[['TOY_CASH',2]]
        return a

def factory(game,mode,seat,arm):
    return (ToyActor(game,mode),ToyActor(game,'control'),ToyActor(game,'null'),ToyActor(game,'control'))

class DriverTests(unittest.TestCase):
    def test_screen_pilot_save_and_reuse_with_toy_engine(self):
        from harvest_experiment import rollout
        data=payload();keys=[dict(seed=s,seat=p,opponent='livestock_fertilizer',arm='coordinated') for s,p in [(1601,0),(1601,1),(1602,0)]]
        jobs=[dict(**k,sha256=str(i),path='unused') for i,k in enumerate(keys)]
        env=SimpleNamespace(game=GAME,make_environment=lambda seed:ToyEnv())
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);out=home/'outputs'
            (home/'kaggriculture_sale_timing/outputs').mkdir(parents=True)
            pd.DataFrame([dict(**k,coins_guarded=3000.,opponent_coins_guarded=3000.) for k in keys]).to_csv(home/'kaggriculture_sale_timing/outputs/final_comparisons.csv',index=False)
            with patch.object(runner,'OUT',out),patch.object(runner,'preflight',return_value=(home,env,'toy-fp')),patch.object(runner,'test_stage',return_value={'tests':0,'scope':'test-harness-only'}),patch.object(runner,'source_jobs',return_value=({},jobs)),patch.object(runner,'load_source',side_effect=lambda root,progress,job:(data,{k:job[k] for k in runner.KEYS})),patch('harvest_policy.HarvestPolicy',ToyActor),patch('mechanics.validate',return_value={'sale_cases':0,'demand_cases':0}),patch.object(runner,'log'),patch.object(runner,'emit'),patch('harvest_experiment.rollout',side_effect=lambda *a,**kw:rollout(*a,**kw,actor_factory=factory)):
                runner.screen(home)
                report=runner.read(out/'screen/report.json')
                self.assertEqual((report['observations'],report['action_changes']),(156,3))
                write(out/'screen/status.json',{'status':'COMPLETED','report_sha256':sha(out/'screen/report.json')})
                runner.pilot(home);r=runner.read(out/'pilot/report.json');self.assertEqual(r['paired_results'][0]['coins_delta'],2)
                times={p.name:p.stat().st_mtime_ns for p in (out/'pilot/checkpoints').glob('*')}
                runner.pilot(home)
                self.assertEqual(times,{p.name:p.stat().st_mtime_ns for p in (out/'pilot/checkpoints').glob('*')})
    def test_nonactivation_skips_pilot(self):
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'OUT',Path(d)),patch.object(runner,'preflight',return_value=(Path(d),None,'f')),patch.object(runner,'verify_stage',return_value={'fingerprint':'f','selected_key':None}),patch.object(runner,'log'):
            runner.pilot(Path(d));r=runner.read(Path(d)/'pilot/report.json');self.assertEqual(r['completed_pairs'],0)
    def test_reactive_opponent_observes_changed_state(self):
        from harvest_experiment import rollout,paired
        data=payload();key=dict(seed=1601,seat=0,opponent='livestock_fertilizer',arm='coordinated')
        def reactive(g,mode,seat,arm):
            def enemy(o):
                a={'farmer':['PASS'],'hands':[],'market':[]}
                if o['step']==481 and o['farms'][0]['money']>3000:a['market']=[['TOY_CASH',1]]
                return a
            c,ref,n,_=factory(g,mode,seat,arm);return c,ref,n,enemy
        branches=[rollout(data,key,m,GAME,lambda s:ToyEnv(),dict(coins_guarded=3000.,opponent_coins_guarded=3000.),lambda *a:None,lambda *a,**k:None,reactive) for m in ('control','marginal')]
        r=paired(*branches);self.assertEqual(r['opponent_coins_delta'],1);self.assertEqual(r['coin_margin_delta'],1)
