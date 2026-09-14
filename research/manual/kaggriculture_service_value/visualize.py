"""Ten inline-ready evidence figures per screen; never substitutes missing outcomes."""
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io_utils import atomic,read

def frame(path):
    path=Path(path)
    if not path.exists() or path.stat().st_size<3:return pd.DataFrame()
    try:return pd.read_csv(path)
    except pd.errors.EmptyDataError:return pd.DataFrame()

def empty(title,message):
    f=go.Figure();f.add_annotation(text=message,x=.5,y=.5,xref='paper',yref='paper',showarrow=False)
    f.update_layout(title=title,xaxis={'visible':False},yaxis={'visible':False});return f

def figures(base,rid):
    base=Path(base);root=base/'outputs'/f'round{rid}'/'screen'
    s=frame(root/'states.csv');t=frame(root/'task_features.csv.gz');reg=frame(root/'feature_registry.csv')
    prior=read(base/'reference/input_review.json')['rounds']
    df=pd.DataFrame([{'Round':k,'Changed actions':v['report']['action_changes'],'Screened states':v['report']['observations']} for k,v in prior.items()])
    fs=[px.bar(df,x='Round',y='Changed actions',text='Changed actions',hover_data=['Screened states'],title='Prior evidence: both rounds changed zero sampled actions')]
    if s.empty:
        fs += [empty('Screen not completed','No new experimental values available') for _ in range(9)]
        return fs
    s['source']=s.seed.astype(str)+' / seat '+s.seat.astype(str)
    a=s.groupby('source',as_index=False)[['changed','farm_changed','market_changed']].sum()
    fs.append(px.bar(a,x='source',y=['changed','farm_changed','market_changed'],barmode='group',title='Changed callbacks by source — action/market counts may overlap',labels={'value':'Callbacks','variable':'Change type'}))
    byhour=s.assign(hour=s.step%24).groupby('hour',as_index=False).agg(changed=('changed','sum'),observed=('changed','count'))
    fs.append(px.bar(byhour,x='hour',y='changed',hover_data=['observed'],title='Activation by hour, including newly covered late-day decisions',labels={'hour':'Zero-indexed hour','changed':'Changed callbacks'}))
    if not t.empty:
        fs.append(px.box(t,x='operation',y='score_multiplier',points=False,title='Candidate/reference score multiplier — not realized reward'))
        fs.append(px.scatter(t,x='travel_actions',y='score_multiplier',color='operation',opacity=.35,hover_data=['step','worker','x','y'],title='Task geometry versus proposed score adjustment',labels={'travel_actions':'Outbound movement actions','score_multiplier':'Candidate / reference'}))
        if rid=='19':
            fs.append(px.scatter(t,x='reference_denominator',y='candidate_denominator',color='operation',opacity=.4,title='Collection effort versus conditional cash-completion time',labels={'reference_denominator':'Original outbound + collection','candidate_denominator':'Proposed elapsed callbacks'}))
        else:
            fs.append(px.scatter(t,x='completion_slack',y='score_multiplier',color='operation',opacity=.4,hover_data=['survival_critical','resource_available','deadline_exists'],title='Critical-service slack versus urgency factor',labels={'completion_slack':'Callbacks left after arrival + service'}))
    else:fs += [empty('No eligible task options','Empty task table; no feature value is inferred') for _ in range(3)]
    top=reg.sort_values('distinct_values',ascending=False).head(16) if not reg.empty else reg
    fs.append(px.bar(top,x='distinct_values',y='feature',orientation='h',title='Descriptor variation — not feature importance') if not top.empty else empty('No registry','Screen has no task rows'))
    f=px.scatter(s,x='step',y='candidate_ms',color='source',title='Complete candidate callback on archived states',labels={'step':'Decision step','candidate_ms':'Wall time (milliseconds)'})
    f.add_hline(y=500,line_dash='dash',annotation_text='Local 500 ms gate');fs.append(f)
    field='unavailable_options' if rid=='19' else 'eligible_critical_options'
    grouped=s.groupby(['day','source'],as_index=False)[field].mean()
    fs.append(px.line(grouped,x='day',y=field,color='source',title='Scenario coverage across the season — descriptive, not causal'))
    count=s.groupby('source',as_index=False)[['task_options','unique_tasks']].mean()
    fs.append(px.bar(count,x='source',y=['task_options','unique_tasks'],barmode='group',title='Option count versus distinct tasks: workers do not create new resources',labels={'value':'Mean count per observation'}))
    for f in fs:f.update_layout(height=470,margin=dict(l=75,r=35,t=90,b=90),legend_title_text='')
    return fs

def pair_figures(base,rid):
    base=Path(base);frames=[];tr=[]
    for i in range(1,5):
        c=frame(base/'outputs'/f'round{rid}'/f'pair{i}'/'comparison.csv')
        if not c.empty:frames.append(c)
        x=frame(base/'outputs'/f'round{rid}'/f'pair{i}'/'trajectories.csv')
        if not x.empty:x['block']=f'b{i}';tr.append(x)
    if not frames:return [empty('Endpoint evidence','No paired games executed. This is not a zero gain.')]
    c=pd.concat(frames,ignore_index=True)
    fs=[px.bar(c,x='block',y=m,title=f'Paired development result: {m}',hover_data=['seed','seat','opponent']) for m in ('coins_delta','coin_margin_delta','local_match_score_delta')]
    if tr:
        p=pd.concat(tr).pivot(index=['block','step'],columns='mode',values='own_cash').reset_index();p['delta']=p.candidate-p.control
        fs.append(px.line(p,x='step',y='delta',color='block',title='Continuous cash difference; never sum isolated one-step effects'))
    return fs

def dashboard(base,rid,figs):
    path=Path(base)/'outputs'/f'round{rid}'/'dashboard.html'
    text=['<!doctype html><html><head><meta charset="utf-8"><title>Service-value feature research</title></head><body>',
          f'<h1>Kaggriculture — round {rid}</h1><p>Archived development screen. Features are candidates. No leaderboard score is inferred.</p>']
    text += [f.to_html(full_html=False,include_plotlyjs=True if i==0 else False) for i,f in enumerate(figs)]
    text.append('</body></html>');atomic(path,'\n'.join(text).encode());return path
