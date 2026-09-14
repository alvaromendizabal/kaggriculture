"""A two-expression source-checked fork; original WATER logic remains intact."""
from __future__ import annotations
import ast,hashlib,inspect,textwrap
from copy import deepcopy
from harvest_features import clock,marginal_value
FEED_BLOB='cd180956abf626b772ba761fb37a3fc3a749c225'
ACTIVE_DAYS=(20,21)


def transform_call(source):
    tree=ast.parse(textwrap.dedent(source))
    # These are the two HARVEST terms in the pinned policy, not sale timing or PLACE.
    expressions=[('obs["market"]["prices"][item] * tile["yield_units"]','item'),
                 ('tile["yield_units"] * obs["market"]["prices"][tile["crop"]]','tile["crop"]')]
    targets={ast.dump(ast.parse(s,mode='eval').body,include_attributes=False):(i,it) for i,(s,it) in enumerate(expressions)}
    counts=[0,0]
    class Replace(ast.NodeTransformer):
        def visit_BinOp(self,node):
            key=ast.dump(node,include_attributes=False)
            if key in targets:
                i,item=targets[key];counts[i]+=1
                out=ast.Call(func=ast.Name(id='__harvest_value',ctx=ast.Load()),args=[ast.Name(id='obs',ctx=ast.Load()),ast.Name(id='private',ctx=ast.Load()),ast.parse(item,mode='eval').body,ast.parse('tile["yield_units"]',mode='eval').body],keywords=[])
                return ast.copy_location(out,node)
            return self.generic_visit(node)
    tree=Replace().visit(tree)
    if counts!=[1,1]:raise ValueError(f'Expected two unique HARVEST value terms; got {counts}')
    return ast.fix_missing_locations(tree)


def fork_class(game,mode):
    from kaggriculture_terminal import feed_policy as module
    raw=open(inspect.getsourcefile(module.FeedPolicy),'rb').read()
    if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\x00'+raw).hexdigest()!=FEED_BLOB:
        raise ValueError('FeedPolicy differs from reviewed Git blob; do not patch unknown source')
    if mode not in ('marginal','null'):raise ValueError('Unknown fork mode')
    tree=transform_call(inspect.getsource(module.FeedPolicy.__call__))
    def value(obs,private,item,q):
        if mode=='null' or obs['day'] not in ACTIVE_DAYS:return obs['market']['prices'][item]*q
        return marginal_value(game,item,obs['market']['inventory'][item],q,private['shed'].get(item,0))
    namespace=dict(module.FeedPolicy.__call__.__globals__);namespace['__harvest_value']=value
    exec(compile(tree,'<harvest-value-source-checked-fork>','exec'),namespace)
    return type('HarvestValueFeedPolicy',(module.FeedPolicy,),{'__call__':namespace['__call__']})


class HarvestPolicy:
    def __init__(self,game,mode='marginal',source_arm='coordinated'):
        if mode not in ('control','marginal','null'):raise ValueError('Unknown policy mode')
        from timing_features import FinalSalePolicy
        self.mode=mode;self.shell=FinalSalePolicy(source_arm)
        self.fork=fork_class(game,mode) if mode!='control' else None
        self.last_diagnostics={}
    def prime_recorded_clock(self,previous_step,player):
        self.shell.prime_recorded_clock(previous_step,player)
        if self.fork:
            obj=self.fork('fertilizer');obj.last_step=previous_step;obj.player=player
            self.shell.base.base=obj
    def __call__(self,obs):
        step=clock(obs);action=self.shell(obs)
        self.last_diagnostics={'mode':self.mode,'step':step,'active':self.mode=='marginal' and obs['day'] in ACTIVE_DAYS}
        return deepcopy(action)
