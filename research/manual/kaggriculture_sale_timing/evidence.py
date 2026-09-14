"""Read-only verification and attribution of the returned notebook-09 evidence."""
from pathlib import Path
import gzip
import hashlib
import json


def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(x): return hashlib.sha256(canonical(x)).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def inside(root,rel):
    p=(Path(root)/rel).resolve()
    if not p.is_relative_to(Path(root).resolve()): raise ValueError('Escaping artifact path')
    return p

def load_branch(p):
    d=json.loads(gzip.decompress(Path(p).read_bytes()))
    checksum=d.pop('checksum')
    if digest(d)!=checksum: raise ValueError('Branch checksum mismatch')
    return d['payload']

def diagnose(control,aligned):
    if control['key'] != aligned['key'] or control['initial_state_sha256'] != aligned['initial_state_sha256']:
        raise ValueError('Unpaired branch evidence')
    if control['transitions'] != 23 or aligned['transitions'] != 23:
        raise ValueError('Incomplete source suffix')
    farm_equal=all(all(c[k]==a[k] for k in ('farmer','hands')) for c,a in zip(control['candidate_actions'],aligned['candidate_actions'],strict=True))
    rival_equal=control['opponent_actions']==aligned['opponent_actions']
    ledger=[]
    for branch in (control,aligned):
        for i in range(20,23):
            step=696+i
            cash=branch['trace'][i]
            orders=branch['candidate_actions'][i]['market']
            if any(o[0]!='SELL' for o in orders): raise ValueError('Late ledger contains non-sale cash flows')
            total=0.
            for o in orders:
                item=o[1]
                # With no same-product rival order, this defined one-sided value is realized.
                if any(len(r)>1 and r[1]==item for r in branch['opponent_actions'][i]['market']):
                    raise ValueError('One-sided attribution invalidated by a competing order')
                v=branch['features'][i][f"cash.product.{item}.{branch['variant']}_solo_revenue"]
                ledger.append({'variant':branch['variant'],'step':step,'product':item,'requested_units':o[2],'coins':v})
                total+=v
            if total != cash['own_cash_after']-cash['own_cash_before']:
                raise ValueError('Per-product ledger fails realized cash reconciliation')
    byproduct={}
    for row in ledger:
        byproduct.setdefault(row['product'],{'control':0.,'aligned':0.})[row['variant']]+=row['coins']
    deltas=[{'product':p,**v,'delta':v['aligned']-v['control']} for p,v in sorted(byproduct.items())]
    outcome=aligned['metrics']['coins']-control['metrics']['coins']
    start_equal=control['trace'][20]['own_cash_before']==aligned['trace'][20]['own_cash_before']
    if not farm_equal or not rival_equal or not start_equal or sum(r['delta'] for r in deltas)!=outcome:
        raise ValueError('Attribution conditions not met')
    return {'status':'DIAGNOSIS_RECONCILED','key':control['key'],'cash_delta':outcome,
            'farm_actions_identical':farm_equal,'opponent_actions_identical':rival_equal,
            'ledger':ledger,'product_deltas':deltas,
            'qualification':'Realized late-sale ledger. Does not itself reveal exact public shop composition.'}
