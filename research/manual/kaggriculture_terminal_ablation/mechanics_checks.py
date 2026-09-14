"""Small deterministic final-day fixtures with quantity-aware price expectations.

The starting inventory is large, NOT assumed to be at the price floor. The
pinned WHEAT curve quotes 13 at 1,000,000 inventory, so two units sell for 26.
Expected values are calculated before the transitions, never inferred from the
observed endpoint. This module does not alter any policy or competition metric.
"""
from copy import deepcopy
import math

KINDS = ('early_sale_catches_up', 'last_callback_stranding')


def quoted_sale(game, item, inventory, quantity):
    """Single-seller price path; floor-price sales do not add market inventory."""
    if isinstance(inventory, bool) or not isinstance(inventory, int):
        raise ValueError('Fixture inventory must be an integer')
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not 0 <= quantity <= 100:
        raise ValueError('Fixture quantity must be an integer in 0..100')
    quotes = []
    post = inventory
    for _ in range(quantity):
        price = game.market_price(item, post)
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price < 1:
            raise ValueError('Invalid fixture quote')
        quotes.append(price)
        post += int(price > 1)
    return {'revenue': sum(quotes), 'quotes': quotes, 'post_inventory': post}


def evaluate_fixture(game, transition, project_next, kind, seat=0, inventory=1_000_000):
    """Return complete diagnostics BEFORE the caller applies the acceptance gate.

    No shops are unlocked and steps 716..718 contain no town-center refresh.
    There are no plants/animals or rival orders. Therefore the market is unchanged
    before either scheduled sale, and the ex-ante quoted path is the exact oracle.
    """
    if kind not in KINDS or seat not in (0, 1):
        raise ValueError('Unknown mechanics fixture')
    sale = quoted_sale(game, 'WHEAT', inventory, 2)
    expected_control = 3000 + (sale['revenue'] if kind == KINDS[0] else 0)
    expected_aligned = 3000 + sale['revenue']
    traces, endpoints, checks = [], {}, []
    for variant in ('control', 'aligned'):
        own = {'player': seat, 'day': 29, 'hour': 20, 'step': 716,
               'farms': [game._new_farm(10, 3000) for _ in (0, 1)],
               'private': game._new_private(), 'market': game._new_market(),
               'town': game._new_town()}
        own['private']['inventories'][0] = {'WHEAT': 2}
        own['market']['inventory']['WHEAT'] = inventory
        game._refresh_prices(own['market'])
        if own['market']['prices']['WHEAT'] != sale['quotes'][0]:
            raise ValueError('Fixture refreshed price disagrees with its quoted path')
        rival = {**deepcopy(own), 'player': 1-seat, 'private': game._new_private()}
        views = [None, None]; views[seat] = own; views[1-seat] = rival
        deposit = 716 if kind == KINDS[0] else 718
        for step in range(716, 719):
            action = {'farmer': ['DROP'] if step == deposit else ['PASS'], 'hands': [], 'market': []}
            if ((variant == 'aligned' and step == deposit)
                    or (variant == 'control' and step == deposit + 1)):
                action['market'] = [['SELL', 'WHEAT', 2]]
            before = deepcopy(views)
            result = transition(views[seat], views[1-seat], action,
                                {'farmer': ['PASS'], 'hands': [], 'market': []}, game)
            checks.append(views == before)
            traces.append({'variant': variant, 'step': step, 'action': action,
                           'cash_after': result[seat]['farms'][seat]['money'],
                           'market_wheat_after': result[seat]['market']['inventory']['WHEAT'],
                           'shed_wheat_after': result[seat]['private']['shed'].get('WHEAT', 0),
                           'status_after': result[seat]['status']})
            if step < 718:
                views = project_next(result)
        final = result[seat]
        sold = (kind == KINDS[0] or variant == 'aligned')
        expected_cash = expected_control if variant == 'control' else expected_aligned
        checks.extend([
            all(r['status'] == 'DONE' and r['day']*24+r['hour'] == 719 for r in result),
            final['reward'] == expected_cash,
            final['farms'][seat]['money'] == expected_cash,
            result[1-seat]['reward'] == 3000,
            final['market']['inventory']['WHEAT'] == (sale['post_inventory'] if sold else inventory),
            final['private']['shed'].get('WHEAT', 0) == (0 if sold else 2),
            sum(inv.get('WHEAT', 0) for inv in final['private']['inventories']) == 0,
        ])
        endpoints[variant] = final['reward']
    return {'fixture': kind, 'seat': seat, 'market_item': 'WHEAT',
            'initial_market_inventory': inventory, 'initial_quote': sale['quotes'][0],
            'per_unit_quotes': sale['quotes'], 'expected_single_sale_revenue': sale['revenue'],
            'control_final_cash': endpoints['control'], 'aligned_final_cash': endpoints['aligned'],
            'expected_control_final_cash': expected_control, 'expected_aligned_final_cash': expected_aligned,
            'terminal_cash_delta': endpoints['aligned']-endpoints['control'],
            'expected_delta': expected_aligned-expected_control,
            'oracle': 'Ex-ante unit quotes; no demand events, rival trades, or price overrides',
            'interpreter_calls': 6, 'passed': all(checks), 'trace': traces}
