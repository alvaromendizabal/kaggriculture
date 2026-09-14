"""Causal post-action inventory representation, separate from outcome evaluation.

Inputs are the legal observation, our own proposed farm actions' copied effects,
and two explicit order lists. No opponent inventory, reward, seed, future replay,
or evaluator state is accepted. Cash values are *no-rival-order scenarios*.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from typing import Any, Callable, Mapping, Sequence

SCHEMA = 'post-action-cash-v1'
PRODUCT_FIELDS = (
    'shed_before', 'shed_after', 'shed_delta',
    'control_sell_requested', 'aligned_sell_requested',
    'control_sellable_units', 'aligned_sellable_units',
    'sellable_units_delta', 'control_residual_units', 'aligned_residual_units',
    'control_solo_revenue', 'aligned_solo_revenue', 'solo_revenue_delta',
    'aligned_rule_reserve_units', 'uncovered_sellable_units', 'undercoverage_present',
)
GLOBAL_FIELDS = (
    'remaining_decisions', 'final_callback', 'workers', 'shed_units_before',
    'shed_units_after', 'control_sell_orders', 'aligned_sell_orders',
    'uncovered_sellable_units', 'control_solo_revenue', 'aligned_solo_revenue',
    'solo_revenue_delta', 'control_residual_product_units',
    'aligned_residual_product_units', 'market_orders_changed',
)


def count(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name}: expected numeric count')
    if not math.isfinite(value) or value < 0 or int(value) != value:
        raise ValueError(f'{name}: invalid count')
    return int(value)


def counts(values: Mapping, name: str) -> dict[str, int]:
    if not isinstance(values, Mapping):
        raise ValueError(f'{name}: expected mapping')
    return {str(k): count(v, name+'.'+str(k)) for k,v in values.items()}


def requested_sales(orders: Sequence, products: Sequence[str]) -> dict[str, int]:
    """Registered terminal order grammar: up to nine SELLs plus a HIRE; no buys.

    Reject unsupported mixtures instead of valuing a made-up sell-only scenario.
    The policy helper emits at most one SELL for each product.
    """
    if not isinstance(orders, (list, tuple)) or len(orders) > 10:
        raise ValueError('Expected at most ten market orders')
    result = {i:0 for i in products}
    hires = 0
    for order in orders:
        if not isinstance(order, (list, tuple)) or not order:
            raise ValueError('Malformed order')
        if order[0] == 'HIRE' and len(order) == 1:
            hires += 1
            if hires > 1: raise ValueError('Terminal rule permits at most one hire')
        elif len(order) == 3 and order[0] == 'SELL' and order[1] in result:
            n = count(order[2], 'sell quantity')
            if n <= 0 or result[order[1]]: raise ValueError('Duplicate/empty product order')
            result[order[1]] = n
        else:
            raise ValueError('Outside registered terminal market grammar')
    return result


def solo_sale_value(item: str, inventory: int, quantity: int, price: Callable) -> float:
    """Same-turn single-seller scenario; one-coin sales do not increase supply."""
    quantity = count(quantity, 'quantity')
    if isinstance(inventory,bool) or not isinstance(inventory,int):
        raise ValueError('Market inventory must be integer (negative supply is legal)')
    total = 0.0
    for _ in range(quantity):
        p = float(price(item, inventory))
        if not math.isfinite(p) or p < 1: raise ValueError('Invalid price')
        total += p
        inventory += int(p > 1)
    return total


def non_sell_orders(action: Mapping) -> list:
    return [list(o) for o in action['market'] if o[0] != 'SELL']


def terminal_market_rule(post_action_obs: Mapping, game: Any, fertilizer_value: Callable) -> list[list]:
    """Exact day-29 restriction of FeedPolicy('fertilizer')'s market *rule*.

    Apply it to effects of the actions actually chosen. This is not a new hiring,
    price-forecast, reserve, or purchasing rule. Before day 29 the wrapper uses the
    unchanged FeedPolicy. Rule parity against that source is checked live.
    """
    if post_action_obs['day'] != 29: raise ValueError('Terminal-only market rule')
    obs = post_action_obs
    farm, private = obs['farms'][obs['player']], obs['private']
    remaining = 719 - obs['step']
    if not 1 <= remaining <= 23: raise ValueError('Outside registered terminal callbacks')
    stock = Counter()
    for inv in [private['shed'], *private['inventories']]:
        stock.update(inv)
    reserve_manure = min(3, sum(
        fertilizer_value(obs, (x,y), tile)['net_scenario_value'] > 0
        for y,row in enumerate(farm['tiles']) for x,tile in enumerate(row)
        if isinstance(tile,dict) and tile.get('kind') == 'PLANT'
    ))
    orders = []
    for item in sorted(game.PRODUCTS):
        reserve = reserve_manure if item == 'FERTILIZER' else 0
        held = private['shed'].get(item,0)
        amount = max(0, held - max(0,reserve - (stock[item] - held)))
        if remaining <= 8: amount = held
        if amount: orders.append(['SELL',item,amount])
    if obs['hour'] < 6 and len(farm['hands']) < 3 and len(orders) < 10:
        if farm['money'] >= game._hire_cost(farm['hires_today']): orders.append(['HIRE'])
    requested_sales(orders, game.PRODUCTS)
    return orders


@dataclass
class CashFeatures:
    values: dict[str,float]
    products: list[dict[str,Any]]


def extract_cash_features(before_obs: Mapping, after_private: Mapping,
                          control_orders: Sequence, aligned_orders: Sequence,
                          products: Sequence[str], price: Callable) -> CashFeatures:
    """All descriptors are available before emitting the candidate action.

    This function deliberately has no actual-outcome, rival-action/private,
    engine-state, reward, or replay argument. Extra top-level replay keys are not read.
    """
    step = count(before_obs['step'],'step')
    if not 696 <= step <= 718 or before_obs['day'] != 29:
        raise ValueError('Expected registered day-29 callback')
    if before_obs['hour'] != step % 24: raise ValueError('Clock mismatch')
    before = counts(before_obs['private']['shed'],'shed before')
    after = counts(after_private['shed'],'shed after')
    if sum(before.values()) > 100 or sum(after.values()) > 100:
        raise ValueError('Shed exceeds capacity')
    control = requested_sales(control_orders, products)
    aligned = requested_sales(aligned_orders, products)
    values, rows = {}, []
    for item in sorted(products):
        available = after.get(item,0)
        sold0, sold1 = min(available,control[item]), min(available,aligned[item])
        inv = before_obs['market']['inventory'][item]
        v0 = solo_sale_value(item,inv,sold0,price)
        v1 = solo_sale_value(item,inv,sold1,price)
        row = dict(zip(PRODUCT_FIELDS,(
            before.get(item,0),available,available-before.get(item,0),
            control[item],aligned[item],sold0,sold1,sold1-sold0,
            available-sold0,available-sold1,v0,v1,v1-v0,available-sold1,
            max(0,sold1-sold0),int(sold1>sold0),
        ), strict=True))
        rows.append({'product':item,**row})
        for name,value in row.items(): values[f'cash.product.{item}.{name}'] = float(value)
    globals_ = {
        'remaining_decisions':719-step, 'final_callback':int(step==718),
        'workers':1+len(before_obs['farms'][before_obs['player']]['hands']),
        'shed_units_before':sum(before.values()),'shed_units_after':sum(after.values()),
        'control_sell_orders':sum(o[0]=='SELL' for o in control_orders),
        'aligned_sell_orders':sum(o[0]=='SELL' for o in aligned_orders),
        'uncovered_sellable_units':sum(r['uncovered_sellable_units'] for r in rows),
        'control_solo_revenue':sum(r['control_solo_revenue'] for r in rows),
        'aligned_solo_revenue':sum(r['aligned_solo_revenue'] for r in rows),
        'solo_revenue_delta':sum(r['solo_revenue_delta'] for r in rows),
        'control_residual_product_units':sum(r['control_residual_units'] for r in rows),
        'aligned_residual_product_units':sum(r['aligned_residual_units'] for r in rows),
        'market_orders_changed':int(list(control_orders)!=list(aligned_orders)),
    }
    for name in GLOBAL_FIELDS: values['cash.'+name] = float(globals_[name])
    if len(values) != len(PRODUCT_FIELDS)*len(products)+len(GLOBAL_FIELDS):
        raise AssertionError('Feature schema drift')
    if not all(math.isfinite(x) for x in values.values()): raise ValueError('Non-finite feature')
    return CashFeatures(values,rows)
