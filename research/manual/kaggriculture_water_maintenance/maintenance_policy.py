"""One-predicate in-memory fork; never edits or monkey-patches repository modules.

Only WATER job eligibility is changed. All job priorities, tie rules, market
rules, hiring, other actions, and final-day routing remain source-defined.
"""
from __future__ import annotations
import ast, hashlib, inspect, textwrap, types
from copy import deepcopy
from water_features import features, clock
FEED_BLOB = 'cd180956abf626b772ba761fb37a3fc3a749c225'
ACTIVE_DAYS = (20, 21)

def transform_call(source):
    tree = ast.parse(textwrap.dedent(source))
    expected = ast.dump(ast.parse('not tile["watered_today"]', mode='eval').body, include_attributes=False)
    count = 0

    class Gate(ast.NodeTransformer):

        def visit_If(self, node):
            nonlocal count
            if ast.dump(node.test, include_attributes=False) == expected:
                count += 1
                node.test = ast.copy_location(ast.Call(func=ast.Name(id='__water_gate', ctx=ast.Load()), args=[ast.Name(id='tile', ctx=ast.Load()), ast.Name(id='obs', ctx=ast.Load())], keywords=[]), node.test)
            return self.generic_visit(node)
    new = Gate().visit(tree)
    if count != 1:
        raise ValueError('Expected exactly one source WATER eligibility predicate')
    ast.fix_missing_locations(new)
    return new

def fork_class(game, mode, active_days=ACTIVE_DAYS):
    from kaggriculture_terminal import feed_policy as module
    source_file = inspect.getsourcefile(module.FeedPolicy)
    raw = open(source_file, 'rb').read()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\x00' + raw).hexdigest()
    if blob != FEED_BLOB:
        raise ValueError('FeedPolicy source differs from reviewed Git blob')
    if mode not in ('defer', 'null'):
        raise ValueError('Unknown feature mode')
    method = inspect.getsource(module.FeedPolicy.__call__)
    transformed = transform_call(method)

    def gate(tile, obs):
        if mode == 'null' or obs['day'] not in active_days:
            return not tile['watered_today']
        return bool(features(tile, obs, game.CROPS)['keep_water'])
    namespace = dict(module.FeedPolicy.__call__.__globals__)
    namespace['__water_gate'] = gate
    exec(compile(transformed, '<registered-water-eligibility-fork>', 'exec'), namespace)
    new_method = namespace['__call__']
    return type('MaintenanceFeedPolicy', (module.FeedPolicy,), {'__call__': new_method})

class MaintenancePolicy:

    def __init__(self, game, mode='defer', source_arm='coordinated'):
        if mode not in ('control', 'defer', 'null'):
            raise ValueError('Unknown mode')
        from timing_features import FinalSalePolicy
        self.mode = mode
        self.shell = FinalSalePolicy(source_arm)
        self.fork = fork_class(game, mode) if mode != 'control' else None
        self.last_diagnostics = {}

    def prime_recorded_clock(self, previous_step, player):
        self.shell.prime_recorded_clock(previous_step, player)
        if self.fork is not None:
            base = self.fork('fertilizer')
            base.last_step = previous_step
            base.player = player
            self.shell.base.base = base

    def __call__(self, obs):
        step = clock(obs)
        action = self.shell(obs)
        self.last_diagnostics = {'water_gate_active': self.mode == 'defer' and obs['day'] in ACTIVE_DAYS, 'step': step, 'mode': self.mode}
        return deepcopy(action)
