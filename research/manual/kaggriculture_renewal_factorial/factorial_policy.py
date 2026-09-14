"""Add only early-clear eligibility, preserving the original WATER expression.

No repository file is changed. AST shape and original Git blob are fail-closed.
The null variant uses the same wrapper with an always-false added condition.
"""
from __future__ import annotations
import ast
import hashlib
import inspect
import textwrap
from copy import deepcopy
from lifecycle_features import exhausted_empty, clock, ACTIVE_DAYS

FEED_BLOB = 'cd180956abf626b772ba761fb37a3fc3a749c225'


def transform_call(source: str) -> ast.Module:
    tree = ast.parse(textwrap.dedent(source))
    target = ast.dump(ast.parse('isinstance(tile, dict) and tile.get("kind") == "WEED"', mode='eval').body, include_attributes=False)
    loop = ast.dump(ast.parse('CROP_LAYOUT.items()', mode='eval').body, include_attributes=False)
    counts = [0]
    class Rewrite(ast.NodeTransformer):
        in_crop = False
        def visit_For(self, node):
            old = self.in_crop
            self.in_crop = ast.dump(node.iter, include_attributes=False) == loop
            out = self.generic_visit(node)
            self.in_crop = old
            return out
        def visit_If(self, node):
            if self.in_crop and ast.dump(node.test, include_attributes=False) == target:
                counts[0] += 1
                node.test = ast.copy_location(ast.BoolOp(op=ast.Or(), values=[node.test, ast.parse('__clear_spent(tile, obs)',mode='eval').body]), node.test)
            return self.generic_visit(node)
    tree = Rewrite().visit(tree)
    if counts != [1]:
        raise ValueError(f'Expected exactly one crop-layout clearing condition, got {counts}')
    return ast.fix_missing_locations(tree)


def allowed(tile, obs, crops, mode):
    clock(obs)
    if mode not in ('clear_only', 'null'):
        raise ValueError('Unregistered fork mode')
    return bool(mode == 'clear_only' and obs['day'] in ACTIVE_DAYS and exhausted_empty(tile, obs, crops))


def fork_class(game, mode):
    from kaggriculture_terminal import feed_policy as module
    path = inspect.getsourcefile(module.FeedPolicy)
    with open(path, 'rb') as handle:
        raw = handle.read()
    if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != FEED_BLOB:
        raise ValueError('FeedPolicy source changed; do not patch')
    namespace = dict(module.FeedPolicy.__call__.__globals__)
    namespace['__clear_spent'] = lambda tile, obs: allowed(tile, obs, game.CROPS, mode)
    tree = transform_call(inspect.getsource(module.FeedPolicy.__call__))
    exec(compile(tree, '<clear-only-factorial>', 'exec'), namespace)
    return type('ClearOnlyFeedPolicy', (module.FeedPolicy,), {'__call__': namespace['__call__']})


class FactorialPolicy:
    def __init__(self, game, mode='clear_only', source_arm='coordinated'):
        if mode not in ('control','clear_only','null'):
            raise ValueError('Unregistered mode')
        from timing_features import FinalSalePolicy
        self.mode = mode
        self.shell = FinalSalePolicy(source_arm)
        self.fork = fork_class(game, mode) if mode != 'control' else None
    def prime_recorded_clock(self, previous_step, player):
        self.shell.prime_recorded_clock(previous_step, player)
        if self.fork:
            actor = self.fork('fertilizer')
            actor.last_step, actor.player = previous_step, player
            self.shell.base.base = actor
    def __call__(self, observation):
        clock(observation)
        return deepcopy(self.shell(observation))
