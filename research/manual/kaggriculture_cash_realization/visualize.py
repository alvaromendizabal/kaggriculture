"""Six standalone Plotly charts; output labels do not conflate local cash and rating."""
from pathlib import Path
import html
import pandas as pd
import plotly.express as px
import plotly.io as pio


def charts(outputs,reference):
    outputs,reference=Path(outputs),Path(reference)
    checks=pd.read_csv(outputs/'callback_checks.csv')
    outcomes=pd.read_csv(outputs/'one_step_effects.csv')
    products=pd.read_csv(outputs/'product_features.csv')
    registry=pd.read_csv(outputs/'feature_registry.csv')
    old=pd.read_csv(reference/'notebook07_probe_by_episode.csv')
    counts=old.groupby(['seed','arm'],as_index=False).changed_first_actions.sum()
    f1=px.bar(counts,x='arm',y='changed_first_actions',color='seed',barmode='group',
        title='Prior evidence: first-action changes when an ingredient is removed',
        labels={'changed_first_actions':'Changed worker decisions (not wins)','arm':'Notebook-07 probe'})
    gaps=products.groupby('product',as_index=False).agg(
        states_with_gap=('undercoverage_present','sum'),mean_uncovered_units=('uncovered_sellable_units','mean'))
    f2=px.bar(gaps,x='product',y='states_with_gap',hover_data=['mean_uncovered_units'],
        title='Post-action inventory: states with uncovered sellable goods',
        labels={'states_with_gap':'Saved states (descriptive; not independent trials)'})
    f3=px.scatter(outcomes,x='step',y='own_cash_delta',color='episode_id',
        hover_data=['seed','seat','source_arm','coin_margin_delta'],
        title='One-step cash effects on fixed saved states — NOT season gains',
        labels={'own_cash_delta':'Aligned − control cash after this single step'})
    f3.add_hline(y=0,line_dash='dot')
    terminal=outcomes[outcomes['step']==718].copy()
    terminal['label']=terminal['seed'].astype(str)+' / seat '+terminal['seat'].astype(str)+' / '+terminal['source_arm']
    f4=px.bar(terminal,x='label',y='own_cash_delta',hover_data=['residual_units_delta'],
        title='Last-callback branches only — NOT full-agent competition scores',
        labels={'label':'Frozen episode state','own_cash_delta':'Single final-step cash difference'})
    timings=checks.melt(id_vars=['episode_id','step'],value_vars=['control_callback_ms','aligned_callback_ms'],
                         var_name='arm',value_name='milliseconds')
    f5=px.box(timings,x='arm',y='milliseconds',points='outliers',
        title='Complete terminal callback: original observations, new fork',
        labels={'milliseconds':'Wall-clock milliseconds (harness excluded)'})
    f5.add_hline(y=500,line_dash='dash',annotation_text='500 ms gate')
    top=registry.sort_values(['nonzero_fraction','feature'],ascending=[False,True]).head(24).sort_values('nonzero_fraction')
    f6=px.bar(top,x='nonzero_fraction',y='feature',orientation='h',hover_data=['distinct_values'],
        title='Candidate activation — NOT feature importance or predictive validation',
        labels={'nonzero_fraction':'Fraction of saved states with nonzero value'})
    f6.update_layout(height=850,margin={'l':330})
    figures=[f1,f2,f3,f4,f5,f6]
    for f in figures:
        f.update_layout(font={'size':13},title={'x':0.02},margin={'t':85,'b':85})
    return figures


def save_dashboard(figures,destination,heading='Kaggriculture | Post-action cash realization'):
    sections=['<!doctype html><html><head><meta charset="utf-8"><title>'+html.escape(heading)+'</title></head><body>',
       '<h1>'+html.escape(heading)+'</h1><p>Controlled replay diagnostics. One-step cash deltas must not be added together as a season improvement. No leaderboard rating is measured here.</p>']
    for i,f in enumerate(figures):sections.append(pio.to_html(f,full_html=False,include_plotlyjs=True if i==0 else False))
    sections.append('</body></html>')
    Path(destination).write_text('\n'.join(sections),encoding='utf-8')
