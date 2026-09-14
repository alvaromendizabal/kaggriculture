from pathlib import Path
import contextlib
import io
import tempfile
import time
import unittest
from unittest.mock import patch
import run_next as runner
import visualize
from opportunity_features import extract_opportunities
from fixtures import fixture,RULES


def demo_episodes():
    episodes=[]
    for index in range(3):
        key={'seed':900000+index,'seat':index%2,'opponent':'SYNTHETIC_FIXTURE','arm':'synthetic'}
        episode={'key':key,'states':[],'candidates':[],'choices':[],'parities':[], 'example':None}
        for hour in (0,12,21,22):
            obs=fixture(hands=index,seat=index%2,hour=hour)
            if index==1:obs['private']['shed']={'WHEAT':100}
            if index==2:obs['private']['inventories'][0]={'WHEAT':3,'MILK':5}
            tick=time.perf_counter();result=extract_opportunities(obs,RULES);ms=(time.perf_counter()-tick)*1000
            meta={**key,'episode_id':'synthetic-'+str(index),'step':obs['step']}
            episode['states'].append({**meta,**result.state,'extractor_ms':ms})
            episode['candidates'].extend({**meta,**c} for c in result.candidates)
            episode['choices'].extend({**meta,'source_arm':key['arm'],**c} for c in result.choices)
            episode['example']={'metadata':meta,'candidates':result.candidates,'choices':result.choices,'state':result.state}
        episodes.append(episode)
    return episodes

class Visuals(unittest.TestCase):
    def test_six_plots_and_exports(self):
        # Empty primitive checks are truthfully retained as unverified in synthetic mode.
        with tempfile.TemporaryDirectory() as t,patch.object(runner,'OUT',Path(t)),contextlib.redirect_stdout(io.StringIO()):
            report=runner.summarize(demo_episodes(),[],{}, {'scope':'synthetic'},'demo',time.monotonic(),mode='SYNTHETIC_FIXTURES')
            self.assertEqual(report['status'],'SYNTHETIC_DEMO_ONLY')
            self.assertFalse(report['official_metric_effect_measured'])
            self.assertFalse(report['primitive_parity_passed'])
            data=visualize.load_outputs(t);figs=visualize.figures(data)
            self.assertEqual(len(figs),6)
            p=visualize.export_dashboard(data,figs,Path(t)/'dashboard.html')
            self.assertGreater(p.stat().st_size,10000)
            for rel,h in report['output_sha256'].items():self.assertEqual(runner.sha(Path(t)/rel),h)
    def test_live_report_cannot_pass_without_parity(self):
        with tempfile.TemporaryDirectory() as t,patch.object(runner,'OUT',Path(t)),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError,'requires passed'):
                runner.summarize(demo_episodes(),[],{}, {},'demo',time.monotonic())
    def test_empty_candidates_plot(self):
        with tempfile.TemporaryDirectory() as t,patch.object(runner,'OUT',Path(t)),contextlib.redirect_stdout(io.StringIO()):
            runner.summarize(demo_episodes(),[],{}, {},'demo',time.monotonic(),mode='SYNTHETIC_FIXTURES')
            data=visualize.load_outputs(t);data['candidates']=data['candidates'].query("kind == 'pass'")
            self.assertEqual(len(visualize.figures(data)),6)

if __name__=='__main__':unittest.main()
