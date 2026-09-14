"""Source-checked one-expression fork. No disk edits or global monkey patches."""
from __future__ import annotations
import ast,inspect,hashlib,textwrap
from copy import deepcopy
from feature_common import clock
FEED_BLOB='cd180956abf626b772ba761fb37a3fc3a749c225'

def transform(source):
    tree=ast.parse(textwrap.dedent(source));count=0
    expected=ast.dump(ast.parse('job.priority / (1 + travel)',mode='eval').body,include_attributes=False)
    class Rewrite(ast.NodeTransformer):
        def visit_BinOp(self,node):
            nonlocal count
            if ast.dump(node,include_attributes=False)==expected:
                count+=1
                return ast.copy_location(ast.parse('__service_score(obs, farm, private, index, position, job, travel)',mode='eval').body,node)
            return self.generic_visit(node)
    tree=Rewrite().visit(tree)
    if count!=1:raise ValueError(f'Expected exactly one task-score expression, found {count}')
    return ast.fix_missing_locations(tree)

def fork(game,rid,active):
    from kaggriculture_terminal import feed_policy
    import collection_features,maintenance_features
    cls=feed_policy.FeedPolicy;raw=open(inspect.getsourcefile(cls),'rb').read()
    if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=FEED_BLOB:raise ValueError('Unexpected FeedPolicy source')
    mod={'19':collection_features,'20':maintenance_features}[rid]
    def value(obs,farm,private,index,position,job,travel):
        if not active:return job.priority/(1+travel)
        return mod.score(obs,game,farm,private,index,position,job,travel)
    ns=dict(cls.__call__.__globals__);ns['__service_score']=value
    exec(compile(transform(inspect.getsource(cls.__call__)),'<service-feature-ablation>','exec'),ns)
    return type('ServiceFeedPolicy',(cls,),{'__call__':ns['__call__']})

class FeaturePolicy:
    def __init__(self,game,round_id='19',mode='candidate'):
        if round_id not in ('19','20') or mode not in ('control','null','candidate'):raise ValueError('Unregistered policy')
        from timing_features import FinalSalePolicy
        self.round_id,self.mode=round_id,mode;self.shell=FinalSalePolicy('coordinated')
        self.kind=fork(game,round_id,mode=='candidate') if mode!='control' else None
        if self.kind:self.shell.base.base=self.kind('fertilizer')
    def prime(self,last_step,player):
        self.shell.prime_recorded_clock(last_step,player)
        if self.kind:
            obj=self.kind('fertilizer');obj.last_step=last_step;obj.player=player;self.shell.base.base=obj
    def __call__(self,obs):clock(obs);return deepcopy(self.shell(obs))

def opponent(name):
    if name=='livestock_fertilizer':
        from kaggriculture_livestock.policy import LivestockPolicy
        return LivestockPolicy('fertilizer')
    if name=='crop_full':
        from kaggriculture_research.crop_policy import CropPolicy
        return CropPolicy('full',max_hands=3)
    raise ValueError('Unknown opponent')
