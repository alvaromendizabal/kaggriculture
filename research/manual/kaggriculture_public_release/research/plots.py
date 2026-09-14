"""Research evidence views; invoked only when the owner runs the notebook."""
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def missing(title):
    fig=go.Figure();fig.add_annotation(text='Not executed: no endpoint result is available.',showarrow=False)
    fig.update_layout(title=title);return fig

def figures(root,rid,home):
    root=Path(root);family={'21':'19','22':'20'}[str(rid)]
    old=Path(home)/'kaggriculture_service_value';screen=old/f'outputs/round{family}/screen'
    s=pd.read_csv(screen/'states.csv');s['hour']=s.step%24
    r=pd.read_csv(root/f'outputs/round{rid}/relative_task_features.csv.gz')
    summary=json.loads((root/f'outputs/round{rid}/feature_analysis.json').read_text())
    registry=pd.DataFrame(summary['registry']);g=s.groupby(['seed','seat'],as_index=False).agg(changes=('changed','sum'),observations=('changed','size'))
    g['group']=g.seed.astype(str)+' / seat '+g.seat.astype(str)
    h=s.groupby('hour',as_index=False).agg(changes=('changed','sum'),observations=('changed','size'));h['rate']=h.changes/h.observations
    out=[px.bar(g,x='group',y='changes',title='Reviewed archived activation by dependent source group',labels={'changes':'Changed observations','group':'Development seed / seat'}),
         px.bar(h,x='hour',y='rate',title='Archived action-change rate by hour',labels={'rate':'Fraction of sampled observations'})]
    if family=='19':
        out.append(px.histogram(r,x='cash_rate_gap_to_best',title='Within-worker collection alternatives: conditional rate gap',labels={'cash_rate_gap_to_best':'Conditional coins per callback below best in-scope option'}))
        out.append(px.scatter(r,x='travel_actions',y='candidate_denominator',color='operation',opacity=.3,title='Outbound travel versus conditional time to sell',labels={'candidate_denominator':'Conditional completion callbacks'}))
    else:
        out.append(px.histogram(r,x='slack_above_most_urgent',title='Slack relative to most urgent eligible in-scope task',labels={'slack_above_most_urgent':'Additional callbacks of slack (masked when ineligible)'}))
        out.append(px.scatter(r,x='completion_slack',y='urgency_multiplier',color='operation',opacity=.3,title='Maintenance pressure and score multiplier',labels={'completion_slack':'Callbacks left after service'}))
    out.append(px.bar(registry,x='distinct_values',y='feature',orientation='h',title='Additional diagnostic variation—not feature importance'))
    out.append(px.scatter(s,x='step',y='candidate_ms',color='seed',opacity=.45,title='Archived complete callback measurements',labels={'candidate_ms':'Milliseconds'}))
    pair=old/f'outputs/round{family}/pair1'
    if not (pair/'report.json').exists():
        out.extend([missing(t) for t in ['Own final cash: first fresh pair','Coin margin: first fresh pair','Linked cash difference','Fresh-game callback measurements']])
    else:
        report=json.loads((pair/'report.json').read_text());c=report['comparison']
        endpoints=pd.DataFrame([{'arm':m,'coins':c['coins_'+m],'margin':c['coin_margin_'+m]} for m in ('control','candidate')])
        out.append(px.bar(endpoints,x='arm',y='coins',title='Own final banked cash—one paired development block',labels={'coins':'In-game coins, not leaderboard rating'}))
        out.append(px.bar(endpoints,x='arm',y='margin',title='Final coin margin—same seed, seat and opponent',labels={'margin':'Own minus opponent coins'}))
        t=pd.read_csv(pair/'trajectories.csv');wide=t.pivot(index='step',columns='mode',values='own_cash');wide['difference']=wide['candidate']-wide['control']
        out.append(px.line(wide.reset_index(),x='step',y='difference',title='Continuously advanced trajectories: own-cash difference',labels={'difference':'Candidate minus control coins'}))
        out.append(px.line(t,x='step',y='candidate_ms',color='mode',title='Fresh-game actor callback time',labels={'candidate_ms':'Milliseconds'}))
    for fig in out:fig.update_layout(height=470,margin=dict(l=65,r=35,t=70,b=70))
    return out
