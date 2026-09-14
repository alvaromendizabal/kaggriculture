"""Six interactive Plotly views. Only derived tables are read; no computation jobs."""
from pathlib import Path
import html
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def load_outputs(root):
    root=Path(root)
    return {'report':json.loads((root/'report.json').read_text()),
            'states':pd.read_csv(root/'state_features.csv'),
            'candidates':pd.read_csv(root/'candidate_features.csv.gz'),
            'probes':pd.read_csv(root/'probe_by_episode.csv'),
            'registry':pd.read_csv(root/'feature_registry.csv'),
            'example':json.loads((root/'example_state.json').read_text())}


def empty(title,note):
    f=go.Figure();f.add_annotation(text=note,x=.5,y=.5,showarrow=False,xref='paper',yref='paper')
    f.update_layout(title=title,height=420)
    return f


def figures(data):
    report=data['report']; prefix='SYNTHETIC TEST FIXTURES · ' if report['status']=='SYNTHETIC_DEMO_ONLY' else ''
    figs=[]
    probes=data['probes'].query("arm != 'full'").copy()
    probes['episode_label']=probes.apply(lambda r:f"seed {r['seed']} · seat {r['seat']} · {r['source_arm']}",axis=1)
    fig=px.bar(probes,x='episode_label',y='first_action_change_fraction',color='arm',barmode='group',
               title=prefix+'01 · Does removing a feature change the proposed first action?',
               labels={'first_action_change_fraction':'Within-episode change fraction','episode_label':'Saved development episode','arm':'Removed ingredient'},
               hover_data=['evaluated_worker_states','changed_first_actions'])
    fig.update_yaxes(range=[0,1]);fig.update_layout(height=490);figs.append(fig)
    candidates=data['candidates'];nonpass=candidates[candidates.kind!='pass'].copy()
    # Plotting-only cap. Extraction and exports retain ALL candidates.
    plotted=nonpass.iloc[::max(1,(len(nonpass)+2499)//2500)].copy()
    if len(plotted):
        fig=px.scatter(plotted,x='deadline_slack',y='frozen_bundle_revenue',color='kind',
                 title=prefix+'02 · Visible value versus time left to bank it',
                 labels={'deadline_slack':'Remaining decisions − manual path length','frozen_bundle_revenue':'Conditional incremental sale value (coins)'},
                 hover_data=['episode_id','step','worker_index','candidate_id','arrival_harvest_units','full_rate'])
        fig.add_vline(x=0,line_dash='dash');fig.update_layout(height=470)
    else:fig=empty(prefix+'02 · Deadline/value','No non-PASS candidates in this evidence.')
    figs.append(fig)
    example=pd.DataFrame(data['example']['candidates'])
    matrix=example.pivot(index='worker_index',columns='task_id',values='full_rate').fillna(0)
    fig=go.Figure(go.Heatmap(z=matrix.to_numpy(),x=matrix.columns.tolist(),y=['Worker '+str(v) for v in matrix.index],
                           colorbar={'title':'Coins/action'},hovertemplate='%{y}<br>%{x}<br>Scenario rate %{z:.3f}<extra></extra>'))
    fig.update_layout(title=prefix+'03 · Worker/task opportunities in one saved state',height=max(410,35*len(matrix)+150),
                      xaxis_title='Resource or delivery option',yaxis_title='Original action index');figs.append(fig)
    if len(plotted):
        fig=px.scatter(plotted,x='no_price_impact_rate',y='full_rate',color='product',
               title=prefix+'04 · Headline prices versus quantity-aware sale values',
               labels={'no_price_impact_rate':'Price-impact-omitted rate (coins/action)','full_rate':'Full conditional rate (coins/action)'},
               hover_data=['deadline_slack','price_impact_loss','capacity_value_loss','marginal_harvest_revenue'])
        fig.update_layout(height=470)
    else:fig=empty(prefix+'04 · Price impact','No non-PASS candidates in this evidence.')
    figs.append(fig)
    registry=data['registry'].sort_values('nonzero_fraction')
    fig=px.bar(registry,x='nonzero_fraction',y='feature',orientation='h',
               title=prefix+'05 · Feature activation is not feature importance',
               labels={'nonzero_fraction':'Fraction of candidate rows nonzero','feature':'Candidate descriptor'},
               hover_data=['distinct_values','episodes_with_variation'])
    fig.update_layout(height=max(650,22*len(registry)+130));figs.append(fig)
    states=data['states'].sort_values(['episode_id','step'])
    fig=px.line(states,x='step',y='extractor_ms',color='episode_id',markers=True,
                title=prefix+'06 · Extractor-only timing — not full callback acceptance',
                labels={'step':'Decision step','extractor_ms':'Feature construction (milliseconds)'})
    fig.update_layout(height=450);figs.append(fig)
    for f in figs:f.update_layout(margin=dict(l=65,r=35,t=80,b=100),font=dict(size=13))
    return figs


def export_dashboard(data,figs,path):
    from plotly.io import to_html
    r=data['report']
    body=''.join(to_html(f,full_html=False,include_plotlyjs=True if i==0 else False) for i,f in enumerate(figs))
    scope='Synthetic test fixtures only — not AWS execution or competition evidence.' if r['status']=='SYNTHETIC_DEMO_ONLY' else 'Saved development observations only — no new games, no official score improvement measured.'
    page=f'''<!doctype html><html><head><meta charset="utf-8"><title>Kaggriculture action opportunities</title>
    <style>body{{font:16px/1.6 system-ui;margin:40px auto;max-width:1250px;padding:0 24px}}h1{{line-height:1.15}} .scope{{border-left:4px solid;padding:12px 20px}} code{{font-size:14px}}</style></head><body>
    <p>FEATURE ENGINEERING · ROUND 07</p><h1>From visible harvests to bankable cash</h1>
    <p class="scope">{html.escape(scope)}</p><p>Status: <code>{html.escape(r['status'])}</code>. Full callback: <code>NOT_RUN</code>.</p>
    <p>These plots describe candidate construction and activation. Independent workers may compete for the same resource. Do not sum their values into a forecast of joint income.</p>{body}</body></html>'''
    Path(path).write_text(page)
    return Path(path)
