"""Source-checked, in-memory feature ablation. Never modify repository files.

control/null: original behavior. retire: remove WATER jobs only for empty spent
ongoing plants. renew: same retirement gate, plus reuse the existing weed-DIG job
for those plants within the existing layout and replant horizon. Scores unchanged.
"""
from __future__ import annotations
import ast, hashlib, inspect, textwrap
from copy import deepcopy
from lifecycle_features import clock, exhausted_empty, ACTIVE_DAYS
FEED_BLOB='cd180956abf626b772ba761fb37a3fc3a749c225'
MODES=('control','null','retire','renew')


def transform_call(source):
    tree=ast.parse(textwrap.dedent(source)); counts=[0,0]
    water=ast.dump(ast.parse('not tile["watered_today"]',mode='eval').body,include_attributes=False)
    weed=ast.dump(ast.parse('isinstance(tile, dict) and tile.get("kind") == "WEED"',mode='eval').body,include_attributes=False)
    layout_loop=ast.dump(ast.parse('CROP_LAYOUT.items()',mode='eval').body,include_attributes=False)
    class Rewrite(ast.NodeTransformer):
        in_crop=False
        def visit_For(self,node):
            old=self.in_crop
            self.in_crop=ast.dump(node.iter,include_attributes=False)==layout_loop
            new=self.generic_visit(node);self.in_crop=old
            return new
        def visit_If(self,node):
            sig=ast.dump(node.test,include_attributes=False)
            if sig==water:
                counts[0]+=1
                node.test=ast.copy_location(ast.parse('__keep_water(tile, obs)',mode='eval').body,node.test)
            elif self.in_crop and sig==weed:
                counts[1]+=1
                node.test=ast.copy_location(ast.BoolOp(op=ast.Or(),values=[node.test,ast.parse('__allow_renewal(tile, obs)',mode='eval').body]),node.test)
            return self.generic_visit(node)
    tree=Rewrite().visit(tree)
    if counts!=[1,1]:raise ValueError(f'Expected one WATER condition and one crop-layout WEED condition, got {counts}')
    return ast.fix_missing_locations(tree)


def fork_class(game,mode):
    if mode not in ('null','retire','renew'):raise ValueError('Invalid fork mode')
    from kaggriculture_terminal import feed_policy as module
    raw=open(inspect.getsourcefile(module.FeedPolicy),'rb').read()
    if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\x00'+raw).hexdigest()!=FEED_BLOB:
        raise ValueError('Unexpected FeedPolicy source; do not patch')
    tree=transform_call(inspect.getsource(module.FeedPolicy.__call__))
    def active(obs):return mode!='null' and obs['day'] in ACTIVE_DAYS
    def keep(tile,obs):
        return not tile['watered_today'] and not(active(obs) and exhausted_empty(tile,obs,game.CROPS))
    def renew(tile,obs):
        return mode=='renew' and active(obs) and exhausted_empty(tile,obs,game.CROPS)
    namespace=dict(module.FeedPolicy.__call__.__globals__)
    namespace.update(__keep_water=keep,__allow_renewal=renew)
    exec(compile(tree,'<crop-lifecycle-feature-ablation>','exec'),namespace)
    return type('LifecycleFeedPolicy',(module.FeedPolicy,),{'__call__':namespace['__call__']})


class LifecyclePolicy:
    def __init__(self,game,mode='renew',source_arm='coordinated'):
        if mode not in MODES:raise ValueError('Unknown mode')
        from timing_features import FinalSalePolicy
        self.mode=mode;self.shell=FinalSalePolicy(source_arm)
        self.fork=fork_class(game,mode) if mode!='control' else None
    def prime_recorded_clock(self,previous_step,player):
        self.shell.prime_recorded_clock(previous_step,player)
        if self.fork:
            obj=self.fork('fertilizer');obj.last_step=previous_step;obj.player=player
            self.shell.base.base=obj
    def __call__(self,obs):
        clock(obs)
        return deepcopy(self.shell(obs))
