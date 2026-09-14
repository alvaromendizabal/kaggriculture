"""Current-observation terminal liquidation exposure; not trained or deployed.

Manhattan travel is legal across locked tiles in the pinned game. Delivery
feasibility is per-worker and optimistic: it ignores shared shed capacity, worker
conflicts, future tasks, rival sales and future prices. Values are single-seller
conditional scenarios, not forecasts, labels, or realizable joint profit.
"""
from __future__ import annotations
import math

FIELDS = (
    'callbacks_remaining', 'shed_product_units', 'carried_product_units',
    'individually_deliverable_carried_units', 'deadline_blocked_carried_units',
    'shed_liquidation_scenario_value', 'deliverable_cargo_marginal_scenario_value',
    'deadline_blocked_cargo_marginal_scenario_value', 'shed_room_before_actions',
    'optimistic_delivery_overflow_units', 'workers_with_product_cargo',
    'workers_missing_delivery_deadline',
)


def extract(observation, products, price):
    from cash_features import solo_sale_value, count
    obs = observation
    step = count(obs['step'], 'step')
    if not 696 <= step <= 718 or obs['day'] != 29 or obs['hour'] != step % 24:
        raise ValueError('Terminal-context clock outside registered decisions')
    seat = obs['player']
    if seat not in (0, 1) or len(obs['farms']) != 2:
        raise ValueError('Expected two legal public farms')
    own, private = obs['farms'][seat], obs['private']
    positions = [own['farmer'], *own['hands']]
    if len(positions) != len(private['inventories']):
        raise ValueError('Worker-inventory alignment differs')
    remaining = 719 - step
    feasible = {item: 0 for item in products}
    blocked = {item: 0 for item in products}
    workers_carrying = workers_blocked = total_feasible_inventory = 0
    for pos, inv in zip(positions, private['inventories'], strict=True):
        if len(pos) != 2 or any(isinstance(x, bool) or not isinstance(x, int) or not 0 <= x < 10 for x in pos):
            raise ValueError('Invalid worker position')
        units = {item: count(n, 'inventory.'+item) for item, n in inv.items()}
        actions = min(abs(pos[0]-x) + abs(pos[1]-y) for x, y in ((4,4),(4,5),(5,4),(5,5))) + 1
        ready = actions <= remaining
        goods = sum(units.get(item, 0) for item in products)
        workers_carrying += int(goods > 0)
        workers_blocked += int(goods > 0 and not ready)
        if ready:
            total_feasible_inventory += sum(units.values())
        target = feasible if ready else blocked
        for item in products:
            target[item] += units.get(item, 0)
    shed = {item: count(n, 'shed.'+item) for item, n in private['shed'].items()}
    if sum(shed.values()) > 100:
        raise ValueError('Shed capacity violated')
    shed_value = feasible_value = blocked_value = 0.0
    for item in products:
        supply = obs['market']['inventory'][item]
        q = shed.get(item, 0)
        v0 = solo_sale_value(item, supply, q, price)
        v1 = solo_sale_value(item, supply, q + feasible[item], price)
        v2 = solo_sale_value(item, supply, q + feasible[item] + blocked[item], price)
        shed_value += v0
        feasible_value += v1 - v0
        blocked_value += v2 - v1
    values = (
        remaining, sum(shed.get(i,0) for i in products), sum(feasible.values())+sum(blocked.values()),
        sum(feasible.values()), sum(blocked.values()), shed_value, feasible_value, blocked_value,
        100-sum(shed.values()), max(0,sum(shed.values())+total_feasible_inventory-100),
        workers_carrying, workers_blocked,
    )
    result = {'terminal_context.'+name: float(v) for name,v in zip(FIELDS,values,strict=True)}
    if not all(math.isfinite(v) for v in result.values()):
        raise ValueError('Non-finite terminal exposure')
    return result
