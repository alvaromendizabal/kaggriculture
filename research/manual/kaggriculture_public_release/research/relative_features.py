"""Outcome-blind, within-family diagnostics; not new policy scoring rules.

Inputs must be one observation's feature rows, not future states/rewards. The
rankings cover only the supplied family, not the complete internal job menu.
They are recorded for ablation interpretation, never substituted into the actor.
"""
from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
import math
import time
from typing import Any

COLLECTION_FIELDS = (
    'peer_option_count','peer_best_cash_rate','peer_best_other_cash_rate',
    'cash_rate_gap_to_best','cash_rate_competition_rank',
    'completion_effort_over_fastest','return_share_of_manual_effort',
    'manual_night_both_available','night_minus_manual_sale_offset',
    'carried_and_task_above_current_shed_room','current_shed_stock_to_task_ratio',
    'conditional_cash_rate_share')
MAINTENANCE_FIELDS = (
    'peer_due_option_count','peer_critical_option_count','peer_minimum_critical_slack',
    'slack_above_most_urgent','critical_exclusive_access','feed_blocked_with_shed_stock',
    'worker_wheat_minus_due_feed_jobs','conditional_next_yield_at_survival_risk',
    'additional_missed_refreshes_to_loss','peer_best_urgency_multiplier',
    'urgency_multiplier_gap_to_best','urgency_multiplier_competition_rank')
KEYS = ('seed','seat','opponent','arm','mode','step','worker')

def number(row: dict, name: str) -> float:
    try:
        value=float(row[name])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f'Missing or invalid feature: {name}') from exc
    if not math.isfinite(value):
        raise ValueError(f'Nonfinite feature: {name}')
    return value

def augment(rows: list[dict[str, Any]], family: str) -> list[dict[str, Any]]:
    if family not in ('19','20'):
        raise ValueError('Expected family 19 or 20')
    started=time.monotonic()
    groups: dict[tuple,list[int]]=defaultdict(list)
    for i,row in enumerate(rows):
        if {'reward','rewards','outcome','official_score','label','target'} & set(row):
            raise ValueError('Outcome/label field is prohibited in feature input')
        if 'step' not in row or 'worker' not in row:
            raise ValueError('Explicit observation and worker keys required')
        # Context keys prevent mixing observations across sources or trajectories.
        groups[tuple(str(row.get(k,'')) for k in KEYS)].append(i)
    output=deepcopy(rows)
    for indices in groups.values():
        if time.monotonic()-started>30:
            raise TimeoutError('30-second relative-feature construction deadline')
        peers=[rows[i] for i in indices]
        if family=='19':
            rates=[number(r,'conditional_value_per_callback') for r in peers]
            efforts=[number(r,'candidate_denominator') for r in peers]
            if min(efforts)<=0 or min(rates)<0:
                raise ValueError('Invalid effort or conditional rate')
            best=max(rates);fastest=min(efforts);total=sum(rates)
            for j,i in enumerate(indices):
                r=rows[i];rate=rates[j];manual=number(r,'manual_sale_available')>0
                night=number(r,'night_sale_available')>0;both=manual and night
                q=number(r,'task_units');direct=number(r,'direct_delivery_effort')
                if q<=0 or direct<=0: raise ValueError('Positive stock and effort required')
                vals=[len(peers),best,max((x for k,x in enumerate(rates) if k!=j),default=0),
                      best-rate,1+sum(x>rate for x in rates),efforts[j]-fastest,
                      number(r,'return_actions')/direct,int(both),
                      number(r,'night_sale_offset')-number(r,'manual_sale_offset') if both else 0,
                      max(0,number(r,'own_carried_units')+q-number(r,'shed_free')),
                      number(r,'same_product_in_shed')/q,rate/total if total>0 else 0]
                output[i].update(dict(zip(COLLECTION_FIELDS,vals,strict=True)))
        else:
            eligible=[number(r,'eligible_critical_job')>0 for r in peers]
            slacks=[number(r,'completion_slack') for r in peers]
            minimum=min((s for s,ok in zip(slacks,eligible) if ok),default=-1)
            multipliers=[number(r,'urgency_multiplier') for r in peers];best=max(multipliers)
            due_feed=sum(r.get('operation')=='FEED' for r in peers)
            for j,i in enumerate(indices):
                r=rows[i];critical=number(r,'survival_critical')>0
                already=number(r,'already_serviced')>0
                vals=[len(peers),sum(eligible),minimum,
                      slacks[j]-minimum if eligible[j] else 0,
                      int(eligible[j] and number(r,'exclusive_ready_access')>0),
                      int(r.get('operation')=='FEED' and number(r,'worker_wheat')<=0 and number(r,'shed_wheat')>0),
                      number(r,'worker_wheat')-due_feed,
                      number(r,'nominal_next_yield')*int(critical),
                      2 if already else max(0,2-number(r,'dry_or_unfed_streak')),
                      best,best-multipliers[j],1+sum(x>multipliers[j] for x in multipliers)]
                output[i].update(dict(zip(MAINTENANCE_FIELDS,vals,strict=True)))
    names=COLLECTION_FIELDS if family=='19' else MAINTENANCE_FIELDS
    if any(not math.isfinite(float(r[n])) for r in output for n in names):
        raise ValueError('Nonfinite derived descriptor')
    return output
