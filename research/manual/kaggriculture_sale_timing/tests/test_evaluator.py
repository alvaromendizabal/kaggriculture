"""Full driver wiring on explicit artificial trajectories, not engine acceptance."""
from pathlib import Path
import sys,unittest,tempfile,importlib.util
from copy import deepcopy
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_timing as runner
from timing_features import FinalSalePolicy,select_action
from test_timing import FixtureGame,obs,PRODUCTS

class BaseActor:
    def __init__(self,arm,deposit=718):self.arm=arm;self.deposit=deposit;self.last=695;self.last_diagnostics={}
    def prime_recorded_clock(self,step,player):self.last=step
    def __call__(self,o):
        if o['step']!=self.last+1:raise ValueError('Synthetic chronology broken')
        self.last=o['step'];post=apply(o,{'farmer':['DROP'] if o['step']==self.deposit else ['PASS']})
        before=o['private']['shed'];after=post['private']['shed']
        ctrl={'farmer':['DROP'] if o['step']==self.deposit else ['PASS'],'hands':[],
              'market':[['SELL',p,n] for p,n in (after if self.arm=='sequential' else before).items() if n]}
        ali={**deepcopy(ctrl),'market':[['SELL',p,n] for p,n in after.items() if n]}
        self.last_diagnostics={'control_action':ctrl,'aligned_action':ali,'base_rule_parity':True,'active':True}
        return deepcopy(ctrl)

class Rival:
    def __init__(self,state):self.state=state
    def __call__(self,o):
        if o['step']!=self.state['last_step']+1 or o['player']!=self.state['player']:raise ValueError('Rival state error')
        if 'reward' in o or 'seed' in o:raise ValueError('Leak')
        return {'farmer':['PASS'],'hands':[],'market':[]}

def factory(arm,deposit=718):
    p=FinalSalePolicy.__new__(FinalSalePolicy);p.base=BaseActor(arm,deposit);p.last_diagnostics={};return p

def apply(o,a,game=None):
    x=deepcopy(o)
    if a['farmer']==['DROP']:
        for item,n in x['private']['inventories'][0].items():x['private']['shed'][item]=x['private']['shed'].get(item,0)+n
        x['private']['inventories'][0]={}
    return x

def transition(own,rival,a,ra,game):
    views=[None,None]
    for o,act in [(own,a),(rival,ra)]:views[o['player']]=apply(o,act)
    farms=deepcopy(own['farms']);market=deepcopy(own['market'])
    for o,act in [(own,a),(rival,ra)]:
        v=views[o['player']]
        for order in act['market']:
            item,n=order[1:];n=min(n,v['private']['shed'].get(item,0))
            for _ in range(n):
                q=game.market_price(item,market['inventory'][item]);farms[o['player']]['money']+=q
                market['inventory'][item]+=int(q>1)
            v['private']['shed'][item]-=n
    for p in PRODUCTS:market['prices'][p]=game.market_price(p,market['inventory'][p])
    for v in views:
        v.update(farms=deepcopy(farms),market=deepcopy(market),day=29,hour=23,status='DONE',reward=farms[v['player']]['money']);v.pop('step',None)
    return views

class Cont:
    @staticmethod
    def index_episode(payload):return {(r['observation']['step'],r['player']):r for r in payload['records']}
    @staticmethod
    def legal_observation(o):return {k:deepcopy(o[k]) for k in ('player','step','day','hour','farms','market','town','private')}
    @staticmethod
    def terminal_metrics(result,seat,products):
        mine=result[seat]['reward'];their=result[1-seat]['reward'];priv=result[seat]['private']
        return {'coins':mine,'opponent_coins':their,'coin_margin':mine-their,'local_match_score':float(mine>their)+.5*float(mine==their),
          'residual_product_units':sum(priv['shed'].values())+sum(sum(i.values()) for i in priv['inventories'])}

def assert_source(result,nxt,rewards,step):
    if [r['reward'] for r in result]!=rewards:raise ValueError('Source final reward mismatch')

def payload(arm='coordinated',seat=0):
    rows=[];actor=BaseActor(arm)
    for s in range(696,719):
        own=obs(s);own.update(player=seat,private={'shed':{},'inventories':[{'WHEAT':2}],'seeds':{}},farms=[{'money':3000},{'money':3000}])
        rival=deepcopy(own);rival['player']=1-seat;rival['private']={'shed':{},'inventories':[{}],'seeds':{}}
        ca=actor(own);ra={'farmer':['PASS'],'hands':[],'market':[]}
        rows.extend([{'player':seat,'observation':own,'action':ca},{'player':1-seat,'observation':rival,'action':ra}])
    result=transition(own,rival,ca,ra,FixtureGame())
    return {'records':rows,'rewards':[r['reward'] for r in result]}, {'seed':-1,'seat':seat,'arm':arm,'opponent':'livestock_fertilizer'}

class TestEvaluator(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.old=runner.OUT;runner.OUT=Path(self.tmp.name)
    def tearDown(self):runner.OUT=self.old;self.tmp.cleanup()
    def go(self,p,key):
        mods={'continuation':Cont,'callback':SimpleNamespace(apply_farm_actions=apply),
              'run_cash':SimpleNamespace(isolated_transition=transition,assert_source_transition=assert_source)}
        return runner.evaluate_episode(p,key,FixtureGame(),mods,actor_factory=factory,rival_factory=Rival)
    def test_final_stranding_recovers_cash(self):
        p,k=payload();r=self.go(p,k);self.assertEqual([FixtureGame.market_price('WHEAT',v) for v in (10000,10001)],[25,24]);self.assertEqual(r['result']['coins_delta'],49);self.assertEqual(r['interpreter_calls'],2)
    def test_both_seats(self):
        p,k=payload(seat=1);r=self.go(p,k);self.assertEqual([FixtureGame.market_price('WHEAT',v) for v in (10000,10001)],[25,24]);self.assertEqual(r['result']['coins_delta'],49)
    def test_sequential_negative_control(self):
        p,k=payload(arm='sequential');r=self.go(p,k);self.assertEqual(r['result']['coins_delta'],0);self.assertFalse(r['result']['final_market_changed'])
    def test_prefix_proof_and_feature_count(self):
        p,k=payload();r=self.go(p,k);self.assertEqual(r['result']['prefix_action_parity_checks'],22)
        self.assertEqual(len(r['features']),23);self.assertEqual(len(r['features'][0]),122)
    def test_source_endpoint_guard(self):
        p,k=payload();p['rewards'][0]+=1
        with self.assertRaises(ValueError):self.go(p,k)
    def test_source_action_guard(self):
        p,k=payload();p['records'][0]['action']['farmer']=['NORTH']
        with self.assertRaises(ValueError):self.go(p,k)
    def test_evidence_immutability(self):
        p,k=payload();before=deepcopy(p);self.go(p,k);self.assertEqual(p,before)
    def test_actor_timing_count(self):
        p,k=payload();r=self.go(p,k);self.assertEqual(len(r['latencies']),24)
