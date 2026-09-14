"""Plotly evidence views. Activation and static utility are not feature importance."""
from pathlib import Path
import json,math
import pandas as pd
import plotly.graph_objects as go


def styled(fig,title,subtitle='',y=None):
    fig.update_layout(title={'text':title+('<br><sup>'+subtitle+'</sup>' if subtitle else '')},
        template='plotly_white',font={'family':'Arial','size':13},height=470,
        margin={'l':70,'r':30,'t':90,'b':70},legend={'orientation':'h','y':-0.2})
    if y:fig.update_yaxes(title_text=y)
    return fig

def empty(title,message):
    fig=go.Figure();fig.add_annotation(x=.5,y=.5,xref='paper',yref='paper',text=message,showarrow=False)
    return styled(fig,title)

def prior_figure(reference):
    f=pd.read_csv(Path(reference)/'notebook10_final_comparisons.csv');f=f[f.role=='primary']
    return styled(go.Figure(go.Bar(x=[f"Seed {r.seed} · seat {r.seat}" for r in f.itertuples()],y=f.coins_delta,
               text=f.coins_delta,textposition='auto')),'01 · Preserved final-sale result',
               'Prior notebook 10: three development comparisons; zero local match changes','Final cash difference (coins)')

def screen_figures(out):
    out=Path(out);s=pd.read_csv(out/'screen/states.csv')
    try:r=pd.read_csv(out/'screen/route_candidates.csv.gz')
    except pd.errors.EmptyDataError:r=pd.DataFrame()
    registry=pd.read_csv(out/'screen/feature_registry.csv');figs=[]
    g=s.groupby(['seed','seat'],as_index=False).agg(changes=('farm_commands_changed','sum'),states=('step','count'))
    f=go.Figure(go.Bar(x=[f"Seed {x.seed} · seat {x.seat}" for x in g.itertuples()],y=g.changes,
                      text=[f'{int(c)}/{int(n)} states' for c,n in zip(g.changes,g.states)],textposition='auto'))
    figs.append(styled(f,'02 · Does the new representation change first commands?',
                        'Same recorded states; no simulated outcomes or independent significance test','Changed states'))
    f=go.Figure()
    for (seed,seat),group in s.groupby(['seed','seat']):
        f.add_scatter(x=group.step,y=group.static_utility_delta,mode='lines+markers',name=f'{seed} / seat {seat}')
    figs.append(styled(f,'03 · Change in the unchanged assignment objective',
                        'Current-price route scenario, not banked cash; incumbent remains feasible','Static utility difference'))
    if len(r):
        stride=max(1,math.ceil(len(r)/2500));sample=r.iloc[::stride]
        f=go.Figure(go.Scatter(x=sample['route.solo_utility'],y=sample['route.opportunity_cost_sum'],mode='markers',
            customdata=sample[['worker','first_command','resource_signature']].values,
            hovertemplate='Solo utility %{x}<br>Pressure %{y}<br>Worker %{customdata[0]}<br>First %{customdata[1]}<br>%{customdata[2]}<extra></extra>'))
        f.update_xaxes(title_text='Route solo utility (conditional coin-equivalent)')
        figs.append(styled(f,'04 · Cross-worker opportunity cost',
            f'Evenly spaced display sample of {len(sample):,} / {len(r):,} candidate rows; pressure is approximate','Independent-worker pressure'))
    else:figs.append(empty('04 · Cross-worker opportunity cost','No positive-quantity candidate routes in this slice.'))
    f=go.Figure(go.Bar(y=registry.feature.str.replace('route.','',regex=False),x=registry.nonzero_fraction,orientation='h'))
    f.update_xaxes(title_text='Fraction nonzero',range=[0,1]);f.update_layout(height=600)
    figs.append(styled(f,'05 · Candidate activation, not predictive importance',
                        'Constant-in-slice does not mean globally useless'))
    f=go.Figure()
    for (seed,seat),group in s.groupby(['seed','seat']):
        f.add_scatter(x=group.step,y=group.candidate_callback_ms,mode='lines+markers',name=f'{seed} / seat {seat}')
    f.add_hline(y=500,line_dash='dash',annotation_text='500 ms local acceptance gate')
    figs.append(styled(f,'06 · Complete candidate callback timing',
                        'Includes route generation, original assignment, feature construction and reassignment','Wall time (ms)'))
    return figs


def pilot_figures(out):
    out=Path(out);report=json.loads((out/'pilot/report.json').read_text())
    if not report.get('completed_pairs'):
        return [empty('07 · Endpoint effect',report['decision']),empty('08 · Continuous cash trajectory','Pilot not run: no same-state action activation.')]
    p=pd.read_csv(out/'pilot/paired_results.csv');t=pd.read_csv(out/'pilot/trajectories.csv')
    f=go.Figure()
    labels=[f"{r.role}: {r.seed} / seat {r.seat}" for r in p.itertuples()]
    f.add_bar(x=labels,y=p.coins_delta,name='Own final cash');f.add_bar(x=labels,y=p.coin_margin_delta,name='Coin margin')
    a=styled(f,'07 · Paired terminal outcome',report['decision']+' · one selected development primary, not independent validation','Candidate minus control (coins)')
    f=go.Figure()
    primary=t[t.arm=='coordinated']
    for mode,g in primary.groupby('mode'):f.add_scatter(x=g.step,y=g.own_cash,mode='lines+markers',name=mode)
    b=styled(f,'08 · Linked final-day trajectories','Each branch advances its changed state; opponent reacts to that state','Banked cash (coins)')
    return [a,b]


def dashboard(figures,path):
    from plotly.io import to_html
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    header='''<!doctype html><html><head><meta charset="utf-8"><title>Kaggriculture · Route opportunity</title></head>
<body style="font-family:Arial;max-width:1280px;margin:36px auto;padding:0 24px">
<h1>Kaggriculture | Worker–route opportunity</h1><p>Development evidence only. Static utility, local coins, and match indicators are not leaderboard ratings.</p>'''
    path.write_text(header+''.join(to_html(f,include_plotlyjs=True if i==0 else False,full_html=False) for i,f in enumerate(figures))+'</body></html>')
