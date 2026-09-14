"""Small artificial input rows, not experimental results."""
def collection(**kw):
    r=dict(seed=1,seat=0,opponent='fixture',arm='fixture',step=3,worker=0,x=1,y=1,
        operation='HARVEST',item='WHEAT',conditional_value_per_callback=10,
        candidate_denominator=4,manual_sale_available=1,night_sale_available=1,
        task_units=2,direct_delivery_effort=4,return_actions=1,night_sale_offset=21,
        manual_sale_offset=3,own_carried_units=3,shed_free=4,same_product_in_shed=2)
    r.update(kw);return r

def maintenance(**kw):
    r=dict(seed=1,seat=0,opponent='fixture',arm='fixture',step=3,worker=0,x=1,y=1,
        operation='WATER',item='WHEAT',eligible_critical_job=1,completion_slack=2,
        urgency_multiplier=3,survival_critical=1,already_serviced=0,
        exclusive_ready_access=1,worker_wheat=0,shed_wheat=3,nominal_next_yield=2,
        dry_or_unfed_streak=1)
    r.update(kw);return r
