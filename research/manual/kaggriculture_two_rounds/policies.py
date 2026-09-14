"""One source-checked HARVEST value substitution; frozen source is never modified."""
from __future__ import annotations
import ast,inspect,hashlib,textwrap
from copy import deepcopy
from feature_common import clock
FEED_BLOB='cd180956abf626b772ba761fb37a3fc3a749c225'

def transform(source):
    tree=ast.parse(textwrap.dedent(source));count=0
    expected=ast.dump(ast.parse('tile["yield_units"] * obs["market"]["prices"][tile["crop"]]',mode='eval').body,include_attributes=False)
    class Rewrite(ast.NodeTransformer):
        def visit_Assign(self,node):
            nonlocal count
            if len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='value' and ast.dump(node.value,include_attributes=False)==expected:
                count+=1
                node.value=ast.copy_location(ast.parse('__harvest_value(obs,tile,target,position)',mode='eval').body,node.value)
            return self.generic_visit(node)
    tree=Rewrite().visit(tree)
    if count!=1:raise ValueError(f'Expected one crop HARVEST value expression, found {count}')
    return ast.fix_missing_locations(tree)
def fork(game,round_id,active):
    from kaggriculture_terminal import feed_policy
    import arrival_features,headroom_features
    cls=feed_policy.FeedPolicy;raw=open(inspect.getsourcefile(cls),'rb').read()
    if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=FEED_BLOB:raise ValueError('Unexpected FeedPolicy source')
    feature=arrival_features if round_id=='17' else headroom_features
    def value(obs,tile,target,position):
        if not active or obs['day']==29:return tile['yield_units']*obs['market']['prices'][tile['crop']]
        return feature.adjusted_value(obs,tile,target,position,game)
    ns=dict(cls.__call__.__globals__);ns['__harvest_value']=value
    exec(compile(transform(inspect.getsource(cls.__call__)),'<two-rounds-harvest-feature>','exec'),ns)
    return type('FeatureFeedPolicy',(cls,),{'__call__':ns['__call__']})

class FeaturePolicy:
    def __init__(self,game,round_id='17',mode='candidate'):
        if round_id not in ('17','18') or mode not in ('control','null','candidate'):raise ValueError('Unregistered policy')
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
