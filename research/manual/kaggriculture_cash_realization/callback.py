"""Forward-only terminal callback fork. Frozen repository sources are never patched.

Route menus, assignment objective/tie order, farmer/hand actions, reserve rule,
and hiring rule are held fixed. Arms differ only in whether market orders are
conditioned on the base planner's farm actions or the farm actions actually emitted.
"""
from __future__ import annotations

from copy import deepcopy
from cash_features import extract_cash_features, terminal_market_rule, non_sell_orders

ARMS = ('control', 'aligned')


class CashPolicy:
    def __init__(self, source_arm='coordinated', arm='aligned'):
        if source_arm not in ('sequential','coordinated') or arm not in ARMS:
            raise ValueError('Unknown registered arm')
        from kaggriculture_terminal.feed_policy import FeedPolicy
        self.source_arm, self.arm = source_arm, arm
        self.base = FeedPolicy('fertilizer')
        self.last_diagnostics = {}

    def prime_recorded_clock(self, previous_step, player):
        """Restore only the complete public clock state documented by FeedPolicy.

        It stores exactly arm/last_step/player; no history features or outcomes
        exist in that state. Replay still checks consecutive observations.
        """
        from kaggriculture_terminal.feed_policy import FeedPolicy
        self.base = FeedPolicy.from_state_dict({
            'arm':'fertilizer','last_step':previous_step,'player':player})

    def __call__(self, observation):
        from kaggriculture_research.environment import game
        from kaggriculture_staffing.features import canonical_observation
        from kaggriculture_livestock.features import fertilizer_value
        from kaggriculture_terminal.routing import menus
        from kaggriculture_runtime.routing import assign

        obs = deepcopy(canonical_observation(observation))
        # This preserves the frozen policy's admitted <=3-hands domain. The new
        # workforce extractor is broader, but this callback is NOT broadly certified.
        base_action = self.base(obs)
        if obs['day'] != 29:
            self.last_diagnostics={'active':False,'features':{},'products':[],
                                   'control_action':deepcopy(base_action)}
            return base_action
        base_post = apply_farm_actions(obs,base_action,game)
        rule_at_base = terminal_market_rule(base_post,game,fertilizer_value)
        if rule_at_base != base_action['market']:
            raise ValueError('Terminal rule does not reproduce frozen base orders')
        if self.source_arm == 'coordinated':
            menu, meta = menus(obs)
            selected, joint = assign(menu,int(meta['room']),obs)
            actions = [list(r.actions[0]) if r.actions else ['PASS'] for r in selected]
            farm_action={'farmer':actions[0],'hands':actions[1:],'market':base_action['market']}
        else:
            meta, joint = {}, {}
            farm_action=deepcopy(base_action)
        post=apply_farm_actions(obs,farm_action,game)
        aligned_orders=terminal_market_rule(post,game,fertilizer_value)
        aligned_action={**deepcopy(farm_action),'market':aligned_orders}
        if non_sell_orders(farm_action)!=non_sell_orders(aligned_action):
            raise ValueError('Non-SELL/hiring intervention detected; stop attribution')
        features=extract_cash_features(obs,post['private'],farm_action['market'],
                                       aligned_orders,game.PRODUCTS,game.market_price)
        self.last_diagnostics={
            'active':True,'features':features.values,'products':features.products,
            'control_action':deepcopy(farm_action),'aligned_action':deepcopy(aligned_action),
            'base_rule_parity':True,'routing':{**meta,**joint},
        }
        return farm_action if self.arm=='control' else aligned_action


def apply_farm_actions(obs,action,game):
    """Official unit primitives on an isolated copy, in actual worker-index order."""
    after=deepcopy(obs)
    farm=after['farms'][after['player']];private=after['private']
    actions=[action['farmer'],*action['hands']]
    if len(actions)!=1+len(farm['hands']): raise ValueError('Worker/action alignment mismatch')
    # Atomic PLANT rule is included even though day-29 source policies do not plant.
    demand={}
    for a in actions:
        if len(a)>=2 and a[0]=='PLANT': demand[a[1]]=demand.get(a[1],0)+1
    blocked={c for c,n in demand.items() if n>private['seeds'].get(c,0)}
    for i,a in enumerate(actions):
        actual=['PASS'] if len(a)>=2 and a[0]=='PLANT' and a[1] in blocked else a
        game._apply_unit_action(farm,private,i,actual,10,after['day'],24,100)
    return after
