"""Exact within-block factorial accounting; no p-values from one block."""
from __future__ import annotations
import gzip
import json
import math
from pathlib import Path
from factorial_io import digest, read, sha, inside

MODES=('control','retire','clear_only','renew')
BITS={'control':(0,0),'retire':(1,0),'clear_only':(0,1),'renew':(1,1)}
METRICS=('coins','opponent_coins','coin_margin','local_match_score','residual_product_units')


def historical_branches(previous, hashes):
    previous=Path(previous)
    for name, expected in hashes['files'].items():
        if sha(inside(previous,name))!=expected: raise ValueError('Notebook15 evidence changed: '+name)
    report=read(previous/'outputs/pilot/report.json')
    for stage in ('screen','pilot'):
        status=read(previous/'outputs'/stage/'status.json')
        if status.get('status')!='COMPLETED' or status.get('report_sha256')!=sha(previous/'outputs'/stage/'report.json'):
            raise ValueError('Notebook15 completion receipt invalid')
    if report['completed_branches']!=3: raise ValueError('Expected three completed historical branches')
    branches={}
    for name in hashes['files']:
        if not name.startswith('outputs/pilot/checkpoints/') or not name.endswith('.json.gz'): continue
        doc=json.loads(gzip.decompress(inside(previous,name).read_bytes()))
        checksum=doc.pop('checksum')
        if digest(doc)!=checksum: raise ValueError('Historical semantic checksum differs')
        b=doc['payload']; mode=b['mode']
        if mode not in ('control','retire','renew') or mode in branches: raise ValueError('Duplicate or wrong prior mode')
        if b['key']!=report['selected_key'] or b['suffix_transitions']!=527 or b['null_action_checks']!=527:
            raise ValueError('Historical scope differs')
        if [r['step'] for r in b['trace']]!=list(range(192,719)): raise ValueError('Historical trace incomplete')
        end=b['trace'][-1]; m=b['metrics']
        if m['coins']!=end['own_cash'] or m['opponent_coins']!=end['opponent_cash'] or m['coin_margin']!=m['coins']-m['opponent_coins']:
            raise ValueError('Historical cash metrics do not reconcile')
        if m['local_match_score']!=float(m['coin_margin']>0)+0.5*float(m['coin_margin']==0): raise ValueError('Historical match score inconsistent')
        branches[mode]=b
    if set(branches)!={'control','retire','renew'}: raise ValueError('Incomplete prior factorial cells')
    if len({b['initial_sha256'] for b in branches.values()})!=1: raise ValueError('Initial states differ')
    if branches['control']['control_source_transition_checks']!=526: raise ValueError('Original control was not reproduced')
    return branches,report


def assess(control,candidate):
    delta={k:candidate['metrics'][k]-control['metrics'][k] for k in METRICS}
    if delta['local_match_score']<0:
        competitive='LOCAL_MATCH_REGRESSION'
    elif delta['local_match_score']>0:
        competitive='LOCAL_MATCH_GAIN_SINGLE_KNOWN_BLOCK'
    elif delta['coin_margin']>0:
        competitive='SAME_MATCH_HIGHER_MARGIN'
    elif delta['coin_margin']<0:
        competitive='SAME_MATCH_LOWER_MARGIN'
    else:
        competitive='NO_MATCH_OR_MARGIN_CHANGE'
    if any(delta[k]<0 for k in ('coins','coin_margin','local_match_score')):
        conservative='STOP_NEGATIVE_ENDPOINT'
    elif any(delta[k]>0 for k in ('coins','coin_margin','local_match_score')):
        conservative='PROMISING_KNOWN_BLOCK_ONLY'
    else:
        conservative='STOP_NO_ENDPOINT_BENEFIT'
    return {'contrast':candidate['mode']+'-control',**{k+'_delta':v for k,v in delta.items()},'competitive_interpretation':competitive,'existing_conservative_gate':conservative}


def full_factorial(branches):
    if set(branches)!=set(MODES): raise ValueError('Four factorial cells required; do not impute missing arm')
    if len({digest(b['key']) for b in branches.values()})!=1 or len({b['initial_sha256'] for b in branches.values()})!=1:
        raise ValueError('Factorial block keys/initial states differ')
    rows=[]
    for metric in METRICS:
        f={k:float(branches[k]['metrics'][metric]) for k in MODES}
        if not all(math.isfinite(v) for v in f.values()): raise ValueError('Nonfinite endpoint')
        c0=f['clear_only']-f['control'];c1=f['renew']-f['retire']
        r0=f['retire']-f['control'];r1=f['renew']-f['clear_only']
        interaction=c1-c0
        if not math.isclose(interaction,r1-r0,abs_tol=1e-9): raise ValueError('Interaction algebra failed')
        rows.append({'metric':metric,**f,'clearing_effect_normal_water':c0,'clearing_effect_retired_water':c1,
            'retirement_effect_no_clearing':r0,'retirement_effect_with_clearing':r1,
            'clearing_main_effect_average':(c0+c1)/2,'retirement_main_effect_average':(r0+r1)/2,
            'difference_in_differences':interaction})
    # The difference-in-differences is explicitly not the half-scaled DOE interaction effect.
    return rows
