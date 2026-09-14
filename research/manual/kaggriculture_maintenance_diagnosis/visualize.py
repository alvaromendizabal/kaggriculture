"""Plotly reporting; labels distinguish prior outcomes, scenarios, and accounting."""
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from artifact_io import read,atomic

def figures(base:Path):
    base=Path(base); prior=pd.read_csv(base/'reference/notebook12/outputs/pilot/trajectories.csv')
    curve=prior.pivot(index='step',columns='mode',values='own_cash').reset_index()
    curve['difference']=curve['defer']-curve['control']
    figs=[px.line(curve,x='step',y='difference',title='Recorded notebook-12 own-cash difference — endpoint −396 coins',labels={'difference':'Deferral minus control (coins)'})]
    commands=prior.groupby(['mode','day'],as_index=False)[['water_commands','harvest_commands']].sum()
    figs.append(px.bar(commands,x='day',y='water_commands',color='mode',barmode='group',title='Recorded WATER commands — commands are not productive actions'))
    out=base/'outputs'
    if not (out/'report.json').exists(): return figs
    r=read(out/'report.json'); ledger=pd.read_csv(out/'cash_decomposition.csv')
    own=ledger[ledger.player==0].copy(); own['component']=own.operation+' · '+own.item
    figs.append(go.Figure(go.Waterfall(x=own.component,y=own.cash_delta,measure=['relative']*len(own))).update_layout(title='Reconciled cash difference by trade category (accounting, not isolated causal effects)',yaxis_title='Deferral minus control (coins)'))
    events=pd.read_csv(out/'crop_events.csv.gz')
    if len(events):
        selected=events[(events.player==0)&events.event.isin(['harvest','night_production','water','dry_death','decay_loss','decay_death'])]
        grouped=selected.groupby(['mode','event','crop'],as_index=False).units.sum(); grouped['label']=grouped.crop+' · '+grouped.event
        figs.append(px.bar(grouped,x='label',y='units',color='mode',barmode='group',title='Reconstructed crop flows — harvested, produced, and lost units'))
    else: figs.append(go.Figure().update_layout(title='No crop events in reconstructed data'))
    sells=ledger[(ledger.player==0)&(ledger.operation=='SELL')]
    quantity=sells.melt(id_vars='item',value_vars=['units_control','units_defer'],var_name='branch',value_name='units')
    figs.append(px.bar(quantity,x='item',y='units',color='branch',barmode='group',title='Actually committed sale units, not requested sale quantities'))
    states=pd.read_csv(out/'state_features.csv')
    figs.append(px.line(states,x='step',y='two_refresh_vulnerable_crops',color='mode',title='No-future-WATER scenario: survival buffer from watering now',labels={'two_refresh_vulnerable_crops':'Crops with a two-refresh survival-buffer gain'}))
    plants=pd.read_csv(out/'crop_features.csv.gz')
    sample=plants.groupby(['mode','crop'],as_index=False)[['water_gain_without_harvest','water_gain_with_harvest']].mean()
    long=sample.melt(id_vars=['mode','crop'],var_name='conditional_feature',value_name='mean_units')
    long['label']=long['crop']+' · '+long['mode']
    figs.append(px.bar(long,x='label',y='mean_units',color='conditional_feature',barmode='group',title='Conditional WATER gains with/without a following HARVEST — not realized income'))
    registry=pd.read_csv(out/'feature_registry.csv').sort_values('nonzero_fraction')
    figs.append(px.bar(registry,x='nonzero_fraction',y='feature',orientation='h',title='Feature activation in one development pair — not importance'))
    for f in figs:
        f.update_layout(margin={'l':65,'r':35,'t':85,'b':115},height=500)
    figs[-1].update_layout(height=760)
    return figs

def save_dashboard(base):
    base=Path(base); figs=figures(base)
    chunks=['<!doctype html><html><head><meta charset="utf-8"><title>Kaggriculture — maintenance diagnosis</title></head><body><main style="max-width:1200px;margin:2rem auto;font-family:Arial,sans-serif"><h1>Maintenance loss & interaction features</h1><p>Recorded-action diagnosis. No new policy was evaluated or promoted.</p>']
    for i,f in enumerate(figs): chunks.append(f.to_html(full_html=False,include_plotlyjs=True if i==0 else False))
    chunks.append('</main></body></html>'); path=base/'outputs/maintenance_diagnosis_dashboard.html'
    atomic(path,'\n'.join(chunks).encode());return path,figs
