"""Plotly evidence views. Actual prior data and new-stage outputs are kept distinct."""
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.io import to_html

ORDER=['control','retire','clear_only','renew']
LABELS={'control':'Control','retire':'Retire WATER','clear_only':'Early clear only','renew':'Retire + early clear'}


def finish(fig,title,x=None,y=None):
    fig.update_layout(title={'text':title},height=450,margin=dict(l=65,r=30,t=75,b=65),font=dict(size=14),legend_title_text='',hovermode='closest')
    if x:fig.update_xaxes(title=x)
    if y:fig.update_yaxes(title=y)
    return fig


def note(title,text):
    f=go.Figure();f.add_annotation(text=text,x=.5,y=.5,xref='paper',yref='paper',showarrow=False,font=dict(size=16))
    f.update_xaxes(visible=False);f.update_yaxes(visible=False);return finish(f,title)


def previous(base):
    r=json.loads((Path(base)/'reference/notebook15_pilot_report.json').read_text())
    e=[{'mode':'control','coins':r['paired_results'][0]['coins_control'],'coin_margin':r['paired_results'][0]['coin_margin_control']}]
    for row in r['paired_results']:
        e.append({'mode':row['contrast'].split('-')[0],'coins':row['coins_candidate'],'coin_margin':row['coin_margin_candidate']})
    d=pd.DataFrame(e)
    baseline=d[d['mode']=='control'].iloc[0]
    d=d[d['mode']!='control'].copy()
    d['Own cash change']=d['coins']-baseline['coins']
    d['Coin-margin change']=d['coin_margin']-baseline['coin_margin']
    long=d.melt(id_vars='mode',value_vars=['Own cash change','Coin-margin change'],var_name='metric',value_name='amount')
    a=finish(px.bar(long,x='mode',y='amount',color='metric',barmode='group',text='amount'),'Notebook 15 • cash and margin changes versus control','Prior branch','Difference in coins')
    # Two-dimensional design, empty fourth cell is explicit; no invented result.
    b=go.Figure(go.Heatmap(z=[[e[0]['coins'],None],[e[1]['coins'],e[2]['coins']]],x=['No early clear','Early clear'],y=['Ordinary WATER','Retire WATER'],text=[[f"{e[0]['coins']:,.0f}",'NOT TESTED'],[f"{e[1]['coins']:,.0f}",f"{e[2]['coins']:,.0f}"]],texttemplate='%{text}',showscale=False,hoverongaps=False))
    b=finish(b,'Notebook 15 • the missing factorial cell','Clearing eligibility','Maintenance rule')
    b.add_annotation(x='Early clear',y='Ordinary WATER',text='NOT TESTED',showarrow=False)
    return [a,b]


def all_figures(base):
    base=Path(base);out=base/'outputs';figs=previous(base)
    sp=out/'screen/states.csv';pp=out/'pilot/report.json'
    if sp.exists():
        d=pd.read_csv(sp);daily=d.groupby('day',as_index=False).agg(changes=('changed','sum'),observations=('step','count'))
        figs.append(finish(px.bar(daily,x='day',y='changes',hover_data=['observations']),'Clear-only • full-path first-action activation','Game day (zero-indexed)','Changed callbacks'))
        counts=d.groupby('day',as_index=False)[['clearable_unwatered_plots','clearable_watered_plots']].sum().melt(id_vars='day',var_name='condition',value_name='plant_callbacks')
        figs.append(finish(px.bar(counts,x='day',y='plant_callbacks',color='condition',barmode='group'),'Logged context • clearing and WATER job overlap','Game day','Plant-callback counts (not independent plants)'))
        times=d[['step','candidate_callback_ms','reference_callback_ms','null_callback_ms']].melt(id_vars='step',var_name='callback',value_name='milliseconds')
        f=px.scatter(times,x='step',y='milliseconds',color='callback');f.add_hline(y=500,line_dash='dash',annotation_text='Local 500 ms gate')
        figs.append(finish(f,'Complete callback time • known control states','Decision step','Milliseconds'))
    else:
        figs += [note('Activation screen','Run the live screen; no new measurements yet.'),note('Job overlap','Current-state descriptors are diagnostic only.'),note('Runtime','No AWS timing has been measured here.')]
    if pp.exists():
        r=json.loads(pp.read_text());d=pd.DataFrame(r['endpoints'])
        figs.append(finish(px.bar(d,x='mode',y='coins',text='coins',category_orders={'mode':ORDER},hover_data=['coin_margin','local_match_score','evidence']),'Four-cell endpoint comparison • one known development block','Branch','Own final coins'))
        e=pd.DataFrame(r['factorial_effects']);e=e[e.metric.isin(['coins','coin_margin'])]
        q=e.melt(id_vars=['metric'],value_vars=['clearing_effect_normal_water','clearing_effect_retired_water','difference_in_differences'],var_name='contrast',value_name='delta')
        figs.append(finish(px.bar(q,x='contrast',y='delta',color='metric',barmode='group',text='delta'),'Clearing effect and interaction • no independence or significance claim','Within-block contrast','Difference in coins'))
        t=pd.read_csv(out/'pilot/trajectories.csv')
        basecash=t[t['mode']=='control'][['step','own_cash']].rename(columns={'own_cash':'control_cash'})
        t=t.merge(basecash,on='step',validate='many_to_one');t['cash_difference']=t['own_cash']-t['control_cash']
        figs.append(finish(px.line(t,x='step',y='cash_difference',color='mode',category_orders={'mode':ORDER}),'Cash difference along continuously advanced trajectories','Decision step','Own cash minus control'))
    else:
        figs += [note('Endpoint comparison','Fourth cell has not been evaluated.'),note('Factorial interaction','No effect is filled in before the missing arm is verified.'),note('Cash trajectory','Old branches will be reused; at most one new branch is run.')]
    return figs


def export_dashboard(base,figures=None):
    base=Path(base);figures=figures or all_figures(base)
    head='<!doctype html><html><head><meta charset="utf-8"><title>Kaggriculture • renewal factorial</title><style>body{font-family:Arial,sans-serif;max-width:1200px;margin:40px auto;padding:0 20px}h1{font-size:30px}p{line-height:1.55}section{margin:30px 0}</style></head><body><h1>Renewal × maintenance: controlled feature ablation</h1><p>Historical branches are reused. Current-state features, callback measurements and endpoint outcomes are separate. One repeatedly examined seed block is not independent validation.</p>'
    parts=[to_html(f,include_plotlyjs=True if i==0 else False,full_html=False) for i,f in enumerate(figures)]
    p=base/'outputs/renewal_factorial_dashboard.html';p.parent.mkdir(exist_ok=True)
    p.write_text(head+''.join('<section>'+s+'</section>' for s in parts)+'</body></html>')
    return p
