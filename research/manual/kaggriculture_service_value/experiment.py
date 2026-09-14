"""Evaluator-only seed handling; policies receive isolated legal own observations."""
from __future__ import annotations
from copy import deepcopy
import time,math
from io_utils import digest
from feature_common import clock
import collection_features,maintenance_features

def observations(env):
    root=env.state[0].observation
    return [{'player':p,'step':int(root.day)*24+int(root.hour),'day':int(root.day),'hour':int(root.hour),
      'farms':deepcopy(root.farms),'market':deepcopy(root.market),'town':deepcopy(root.town),
      'private':deepcopy(env.state[p].observation.private)} for p in (0,1)]
def measure(actor,obs,role,emit):
    arg=deepcopy(obs);before=digest(arg);start=time.perf_counter();action=actor(arg);ms=(time.perf_counter()-start)*1000
    emit('CALLBACK',{'step':obs['step'],'role':role,'milliseconds':ms,'action':action})
    if digest(arg)!=before:raise ValueError('Policy mutated observation')
    if not math.isfinite(ms) or ms>500:raise RuntimeError('500 ms callback gate exceeded; measurement saved')
    if set(action)!={'farmer','hands','market'} or len(action['hands'])!=len(obs['farms'][obs['player']]['hands']):raise ValueError('Action/worker mismatch')
    return action,ms

def live_factories(game,round_id,mode,opponent_name):
    from policies import FeaturePolicy,opponent
    return (FeaturePolicy(game,round_id,mode),FeaturePolicy(game,round_id,'control'),FeaturePolicy(game,round_id,'null'),opponent(opponent_name))

def run_game(game,make_environment,round_id,mode,block,emit,log,factory=live_factories):
    env=make_environment(block['seed'])
    if env.configuration.get('seed') is not None:raise ValueError('Seed exposed in actor configuration')
    actor,control,null,rival=factory(game,round_id,mode,block['opponent']);seat=block['seat']
    trace=[];features={'19':[],'20':[]};states={'19':[],'20':[]};changes=0;max_ms=0.;candidate_max_ms=0.;counts={}
    initial=digest(observations(env));first_change=None
    for step in range(719):
        obs=observations(env);own=obs[seat]
        if clock(own)!=step:raise ValueError('Live clock mismatch')
        actual,ams=measure(actor,own,'candidate',emit);reference,rms=measure(control,own,'same_state_control',emit)
        shadow,nms=measure(null,own,'same_state_null',emit);enemy,ems=measure(rival,obs[1-seat],'opponent',emit)
        if reference!=shadow:raise ValueError('Null fork differs from unchanged control')
        changed=actual!=reference
        if (mode=='control' or step//24==29) and changed:raise ValueError('Feature intervention escaped its registered scope')
        if changed and first_change is None:first_change=step
        changes+=int(changed);max_ms=max(max_ms,ams,rms,nms,ems);candidate_max_ms=max(candidate_max_ms,ams)
        commands=[actual['farmer'],*actual['hands']]
        for cmd in commands:counts[cmd[0]]=counts.get(cmd[0],0)+1
        # Record outcome-blind features separately, sampled at fixed times for both rounds.
        if step%12==0 and step<696:
            for rid,module in [('19',collection_features),('20',maintenance_features)]:
                rr,ss=module.extract(own,game)
                features[rid].extend([{'step':step,**r} for r in rr]);states[rid].append({'step':step,**ss})
        action=[None,None];action[seat]=actual;action[1-seat]=enemy;env.step(action)
        post=observations(env)
        ownfarm=post[seat]['farms'][seat]
        crop_counts={}
        for row in ownfarm['tiles']:
            for t in row:
                if isinstance(t,dict) and t.get('kind')=='PLANT':crop_counts[t['crop']]=crop_counts.get(t['crop'],0)+1
        trace.append({'step':step,'day':step//24,'own_cash':ownfarm['money'],'opponent_cash':post[seat]['farms'][1-seat]['money'],
          'own_cash_before':own['farms'][seat]['money'],'changed':changed,'candidate_ms':ams,'opponent_ms':ems,
          'reference_ms':rms,'null_ms':nms,'action':actual,'reference_action':reference,'opponent_action':enemy,
          'observed_market':own['market'],'own_crop_counts_after':crop_counts})
        if (step+1)%120==0:log('GAME_PROGRESS',block=block['id'],mode=mode,completed=step+1,total=719)
    final=observations(env)
    if [s.status for s in env.state]!=['DONE','DONE'] or len(env.steps)!=720:raise ValueError('Incomplete official horizon')
    rewards=[float(s.reward) for s in env.state]
    if any(rewards[p]!=final[p]['farms'][p]['money'] for p in (0,1)):raise ValueError('Reward/cash mismatch')
    margin=rewards[seat]-rewards[1-seat];priv=final[seat]['private']
    residual=sum(q for inv in [priv['shed'],*priv['inventories']] for item,q in inv.items() if item in game.PRODUCTS)
    return {'block':block,'mode':mode,'round':round_id,'initial_sha256':initial,'final_sha256':digest(final),
      'transitions':719,'null_checks':719,'action_changes':changes,'first_change_step':first_change,'callback_max_ms':max_ms,'candidate_callback_max_ms':candidate_max_ms,
      'metrics':{'coins':rewards[seat],'opponent_coins':rewards[1-seat],'coin_margin':margin,'local_match_score':float(margin>0)+.5*float(margin==0),'residual_product_units':residual},
      'command_counts':counts,'trace':trace,'features':features,'states':states}

def compare(control,candidate):
    if control['block']!=candidate['block'] or control['initial_sha256']!=candidate['initial_sha256']:raise ValueError('Unmatched paired initial state')
    if any(b['transitions']!=719 or b['null_checks']!=719 for b in (control,candidate)):raise ValueError('Incomplete pair')
    out={'block':candidate['block']['id'],**candidate['block'],'action_changes':candidate['action_changes']}
    for m in control['metrics']:
        out[m+'_control']=control['metrics'][m];out[m+'_candidate']=candidate['metrics'][m];out[m+'_delta']=candidate['metrics'][m]-control['metrics'][m]
    out['conservative_guard']='STOP_NEGATIVE_ENDPOINT' if any(out[m+'_delta']<0 for m in ('coins','coin_margin','local_match_score')) else 'NO_NEGATIVE_ENDPOINT'
    out['decision']=out['conservative_guard'] if out['conservative_guard'].startswith('STOP') else ('STOP_NO_TRAJECTORY_ACTIVATION' if not out['action_changes'] else ('NO_ENDPOINT_BENEFIT' if all(out[m+'_delta']==0 for m in ('coins','coin_margin','local_match_score')) else 'PROMISING_DEVELOPMENT_ONLY'))
    out['competitive_interpretation']=('MATCH_IMPROVED' if out['local_match_score_delta']>0 else 'MATCH_WORSE' if out['local_match_score_delta']<0 else 'SAME_MATCH_HIGHER_MARGIN' if out['coin_margin_delta']>0 else 'SAME_MATCH_LOWER_MARGIN' if out['coin_margin_delta']<0 else 'UNCHANGED_MATCH_AND_MARGIN')
    return out
