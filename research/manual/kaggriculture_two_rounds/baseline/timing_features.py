"""Causal sale-timing candidates; known-demand paths are scenarios, not forecasts.

Inputs are the current player's legal observation and inventory after that player's
proposed farm actions. No evaluator rewards, seeds, future shops, or opponent orders
enter the interface. Horizon unavailable values are zero with an explicit mask.
"""
from __future__ import annotations
from copy import deepcopy
import math

END = 718
HORIZONS = (1, 4)


def clock(obs: dict) -> int:
    day, hour = obs['day'], obs['hour']
    if isinstance(day, bool) or isinstance(hour, bool) or not isinstance(day, int) or not isinstance(hour, int):
        raise ValueError('Clock must contain integers')
    step = day * 24 + hour
    if not 0 <= hour < 24 or not 0 <= step <= END:
        raise ValueError('Outside registered default decision horizon')
    if obs.get('step') is not None and obs['step'] != step:
        raise ValueError('Conflicting public clock')
    return step


def nonnegative_integer(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or int(x) != x or x < 0:
        raise ValueError('Expected nonnegative integer quantity')
    return int(x)


def sale_path(item, inventory, quantity, price_fn):
    """Exact one-sided liquidation; the one-coin floor does not add supply."""
    n = nonnegative_integer(quantity)
    if isinstance(inventory, bool) or not isinstance(inventory, int):
        raise ValueError('Inventory must be an integer; negative inventory is allowed')
    value = 0.0
    for j in range(n):
        price = price_fn(item, inventory)
        if not math.isfinite(price) or price < 1:
            raise ValueError('Invalid price')
        if price == 1:
            return value + (n-j), inventory
        value += price
        inventory += 1
    return value, inventory


def known_demand(game, shops, item, step, horizon):
    """Demand after market at step..step+horizon-1, before the later sale.

    Registered default intervals: shop 4, town center 24. Current shops only;
    duplicates count independently. The runner restricts all samples to day 29.
    """
    horizon = nonnegative_integer(horizon)
    if item not in game.PRODUCTS:
        raise ValueError('Unknown product')
    if any(s not in game.SHOPS for s in shops):
        raise ValueError('Unknown visible shop')
    per_event = sum((2 if len(game.SHOPS[s]) == 1 else 1) for s in shops if item in game.SHOPS[s])
    events = sum(t % 4 == 0 for t in range(step, step+horizon))
    center = sum(t % 24 == 0 for t in range(step, step+horizon)) if item in game.TOWN_CENTER_PRODUCTS else 0
    return per_event * events + center


def extract(obs, after_private, game):
    step = clock(obs)
    if obs['day'] != 29:
        raise ValueError('Research feature scope is final day only')
    if game._resolve_market_params(obs['market'].get('params')) != game.MARKET_PARAMS:
        raise ValueError('Only registered default market curves supported')
    values = {'sale_timing.last_callback': float(step == END),
              'sale_timing.future_sale_callbacks': float(END-step),
              'sale_timing.next_shop_event_offset': float((-step) % 4)}
    for item in game.PRODUCTS:
        inv = obs['market']['inventory'][item]
        quote = game.market_price(item, inv)
        if obs['market']['prices'][item] != quote:
            raise ValueError('Observed price differs from registered curve')
        quantity = nonnegative_integer(after_private['shed'].get(item, 0))
        value, _ = sale_path(item, inv, quantity, game.market_price)
        prefix = 'sale_timing.'+item+'.'
        values.update({prefix+'post_action_units': float(quantity), prefix+'current_quote': float(quote),
                       prefix+'sell_now_solo_value': value})
        for horizon in HORIZONS:
            available = step+horizon <= END
            demand = known_demand(game, obs['town']['unlocked_shops'], item, step, horizon) if available else 0
            future = sale_path(item, inv-demand, quantity, game.market_price)[0] if available else 0.0
            p = prefix+f'h{horizon}.'
            values.update({p+'available': float(available), p+'known_demand_units': float(demand),
                           p+'demand_only_quote': float(game.market_price(item, inv-demand)) if available else 0.,
                           p+'demand_only_value': future,
                           p+'conditional_holding_premium': future-value if available else 0.})
    if len(values) != 120 or not all(math.isfinite(v) for v in values.values()):
        raise ValueError('Timing feature schema drift')
    return values


def select_action(obs, control, aligned):
    """A fixed horizon gate, not a fitted threshold: keep all early actions exact."""
    step = clock(obs)
    if any(control[k] != aligned[k] for k in ('farmer','hands')):
        raise ValueError('The comparison changes farm actions')
    non_sell = lambda a: [o for o in a['market'] if not o or o[0] != 'SELL']
    if non_sell(control) != non_sell(aligned):
        raise ValueError('The comparison changes non-SELL orders')
    if step == END and (non_sell(control) or len(aligned['market']) > 10):
        raise ValueError('Final intervention requires SELL-only orders within the official limit')
    return deepcopy(aligned if step == END else control)


class FinalSalePolicy:
    """Full terminal callback, built on the already-tested exact control path.

    It computes the control on every observation, maintaining identical memory.
    It returns the aligned action only at the final legal decision (step 718).
    Diagnostic timing features are deliberately computed outside callback timing.
    """
    def __init__(self, source_arm='coordinated'):
        from callback import CashPolicy
        self.base = CashPolicy(source_arm, 'control')
        self.last_diagnostics = {}

    def prime_recorded_clock(self, previous_step, player):
        self.base.prime_recorded_clock(previous_step, player)

    def __call__(self, obs):
        control = self.base(obs)
        diag = deepcopy(self.base.last_diagnostics)
        aligned = diag.get('aligned_action', control)
        action = select_action(obs, control, aligned)
        diag['final_sale_gate'] = int(clock(obs) == END)
        diag['actual_market_changed'] = action['market'] != control['market']
        self.last_diagnostics = diag
        return action
