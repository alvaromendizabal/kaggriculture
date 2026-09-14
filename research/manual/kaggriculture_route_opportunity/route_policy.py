"""Forward-only complete callback; keeps frozen repository modules unchanged."""
from __future__ import annotations
from copy import deepcopy

class RouteOpportunityPolicy:
    def __init__(self, source_arm='coordinated', mode='opportunity'):
        if source_arm not in ('coordinated','sequential') or mode not in ('control','opportunity'):
            raise ValueError('Unregistered policy')
        from kaggriculture_terminal.feed_policy import FeedPolicy
        self.base=FeedPolicy('fertilizer');self.source_arm=source_arm;self.mode=mode
        self.last_diagnostics={};self.route_rows=[]

    def prime_recorded_clock(self, previous_step, player):
        from kaggriculture_terminal.feed_policy import FeedPolicy
        self.base=FeedPolicy.from_state_dict({'arm':'fertilizer','last_step':previous_step,'player':player})

    def __call__(self, observation):
        from kaggriculture_staffing.features import canonical_observation
        from kaggriculture_terminal import routing
        from kaggriculture_runtime.routing import assign
        from kaggriculture_livestock.features import fertilizer_value
        from callback import apply_farm_actions
        from cash_features import terminal_market_rule
        from route_features import select_plan
        obs=deepcopy(canonical_observation(observation));self.route_rows=[]
        base_action=self.base(obs)
        if obs['day']!=29:
            self.last_diagnostics={'active':False}
            return base_action
        post_base=apply_farm_actions(obs,base_action,routing.game)
        if terminal_market_rule(post_base,routing.game,fertilizer_value)!=base_action['market']:
            raise ValueError('Base market rule parity failed')
        if self.source_arm=='coordinated':
            _,diag,rows,original,meta=select_plan(obs,routing,assign,self.mode)
            self.original_menus=original;self.route_meta=meta
            chosen=diag['chosen_commands'];inc=diag['baseline_commands']
            self.route_rows=rows
        else:
            chosen=[base_action['farmer'],*base_action['hands']];inc=deepcopy(chosen)
            diag={'static_key_improved':False,'farm_commands_changed':False,
                  'baseline_utility':0.,'candidate_utility':0.,'static_utility_delta':0.,
                  'incumbent_preserved':True,'menus_changed':0,'routes_feasible':0,
                  'new_admitted_routes':0,'baseline_commands':inc,'chosen_commands':chosen}
        def package(commands):
            action={'farmer':commands[0],'hands':commands[1:],'market':deepcopy(base_action['market'])}
            if obs['step']==718:
                after=apply_farm_actions(obs,action,routing.game)
                action['market']=terminal_market_rule(after,routing.game,fertilizer_value)
            return action
        actual=package(chosen);control=package(inc)
        non_sell=lambda a:[o for o in a['market'] if not o or o[0]!='SELL']
        if non_sell(actual)!=non_sell(control):raise ValueError('Non-sale rule changed')
        if obs['step']<718 and actual['market']!=control['market']:
            raise ValueError('Early market rule changed on same state')
        self.last_diagnostics={'active':True,'base_rule_parity':True,'routing':diag,
                               'same_state_control_action':control,
                               'final_sale_gate':obs['step']==718,
                               'mode':self.mode,'feature_rows':len(self.route_rows)}
        return actual
