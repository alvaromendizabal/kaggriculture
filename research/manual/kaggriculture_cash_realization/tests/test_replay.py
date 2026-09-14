"""End-to-end replay/checkpoint wiring with an explicitly synthetic engine/source.

This exercises the implementation harness, not pinned-Kaggle action equivalence.
Live official-engine parity remains a mandatory gate in notebook 08.
"""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from fixtures import fixture,ToyGame
from test_callback import dependencies
from callback import CashPolicy
import run_cash as runner


class ReplayHarnessTests(unittest.TestCase):
    def test_seven_synthetic_episodes_checkpoint_and_reuse(self):
        modules=dependencies()
        art=ModuleType('kaggriculture_research.artifacts')
        art.load_checkpoint=lambda p,lineage:json.loads(Path(p).read_text())
        exp=ModuleType('kaggriculture_staffing.experiment')
        exp.validate_episode=lambda payload,key:None
        modules[art.__name__]=art;modules[exp.__name__]=exp
        with tempfile.TemporaryDirectory() as d,patch.dict(sys.modules,modules):
            root=Path(d)/'raw';out=Path(d)/'out';root.mkdir();out.mkdir()
            manifest=[]
            for n in range(7):
                key={'seed':1601+n%2,'seat':n%2,'opponent':'synthetic','arm':'coordinated' if n<4 else 'sequential'}
                # Make source key unique without pretending these are original blocks.
                key['opponent']='synthetic-'+str(n)
                seat=key['seat'];records=[]
                for step in (0,24,695):
                    obs=fixture(step=step,seat=seat)
                    actor=CashPolicy(key['arm'],'control');actor.prime_recorded_clock(None if step==0 else step-1,seat)
                    records.append({'player':seat,'observation':obs,'action':actor(obs)})
                own=fixture(step=696,seat=seat);own['private']['inventories'][0]={'WHEAT':3}
                rival=deepcopy(own);rival['player']=1-seat;rival['private']['inventories']=[{}]
                actor=CashPolicy(key['arm'],'control');actor.prime_recorded_clock(695,seat)
                for step in range(696,719):
                    a=actor(own);b={'farmer':['PASS'],'hands':[],'market':[]}
                    records += [{'player':seat,'observation':deepcopy(own),'action':deepcopy(a)},
                                {'player':1-seat,'observation':deepcopy(rival),'action':deepcopy(b)}]
                    result=runner.isolated_transition(own,rival,a,b,ToyGame)
                    own={k:v for k,v in result[seat].items() if k not in ('status','reward')}
                    rival={k:v for k,v in result[1-seat].items() if k not in ('status','reward')}
                    own['step']=rival['step']=step+1
                payload={'records':records,'rewards':[result[0]['reward'],result[1]['reward']]}
                path=root/f'episode-{n}.json';path.write_text(json.dumps(payload))
                manifest.append({**key,'path':path.name,'sha256':runner.sha(path)})
            runner.write(root/'reports/staffing_progress.json',{
                'completed_games':7,'complete':False,'artifact_manifest':manifest,'lineage':{}})
            with patch.object(runner,'OUT',out),contextlib.redirect_stdout(io.StringIO()):
                first=runner.replay(root,ToyGame,'synthetic-only')
                second=runner.replay(root,ToyGame,'synthetic-only')
            self.assertEqual(len(first),7)
            self.assertEqual(sum(len(e['states']) for e in first),161)
            self.assertEqual(len(list((out/'checkpoints').glob('*.gz'))),7)
            self.assertEqual(first,second)
            self.assertTrue(all(r['recorded_transition_parity'] for e in first for r in e['effects']))
