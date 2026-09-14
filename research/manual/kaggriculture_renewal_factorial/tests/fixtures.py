"""Explicit artificial fixtures; these are not a substitute for the live engine."""
from copy import deepcopy
from types import SimpleNamespace
CROPS = {'WHEAT': dict(seed=10, first_yield_day=2, max_yield_day=4, interval=0, max_yield=6, ongoing=False), 'CARROT': dict(seed=20, first_yield_day=2, max_yield_day=3, interval=0, max_yield=4, ongoing=False), 'TOMATO': dict(seed=50, first_yield_day=8, max_yield_day=8, interval=1, max_yield=4, ongoing=True), 'STRAWBERRY': dict(seed=100, first_yield_day=10, max_yield_day=10, interval=2, max_yield=4, ongoing=True), 'MELON': dict(seed=80, first_yield_day=10, max_yield_day=12, interval=0, max_yield=6, ongoing=False)}

def plant(crop='WHEAT', planted=18, units=2, dry=0, watered=False, fertile=-1, life=-1):
    return dict(kind='PLANT', crop=crop, planted_day=planted, yield_units=units, consecutive_unwatered=dry, watered_today=watered, fertilized_until_day=fertile, max_lifespan_step=life)

def observation(day=20, hour=0, tile=None):
    farm = dict(farmer=[4, 4], hands=[], money=3000.0, hires_today=0, unlocked_quadrants=['NW'], tiles=[[None] * 10 for _ in range(10)])
    if tile is not None:
        farm['tiles'][4][4] = deepcopy(tile)
    return dict(player=0, day=day, hour=hour, step=day * 24 + hour, farms=[farm, deepcopy(farm)], market={'inventory': {k: 10000 for k in CROPS}, 'prices': {k: 25 for k in CROPS}}, town={'unlocked_shops': []}, private={'shed': {'WHEAT': 0}, 'inventories': [{}], 'seeds': {}})
GAME = SimpleNamespace(CROPS=CROPS, PRODUCTS=list(CROPS), MARKET_PARAMS={}, _resolve_market_params=lambda x: {}, market_price=lambda item, stock: 25)

class ToyEnv:
    """Clock/state-branch fixture; NOT Kaggriculture economics or mechanics."""

    def __init__(self):
        self.configuration = {'seed': None}
        self.steps = [None]
        self.t = 0
        obs = observation(0, 0)
        self.farms = obs['farms']
        self.market = obs['market']
        self.town = obs['town']
        self.privates = [deepcopy(obs['private']), deepcopy(obs['private'])]
        self.sync()

    def sync(self):
        self.state = [SimpleNamespace(observation=SimpleNamespace(player=p, day=self.t // 24, hour=self.t % 24, step=self.t, farms=self.farms, market=self.market, town=self.town, private=self.privates[p]), reward=self.farms[p]['money'] if self.t == 719 else 0, status='DONE' if self.t == 719 else 'ACTIVE') for p in (0, 1)]

    def step(self, actions):
        for p, a in enumerate(actions):
            for order in a['market']:
                if order[0] == 'TOY_CASH':
                    self.farms[p]['money'] += order[1]
        self.t += 1
        self.steps.append(None)
        self.sync()

def toy_factory(game, mode, seat, arm):

    def base(obs):
        return {'farmer': ['PASS'], 'hands': [], 'market': []}

    def candidate(obs):
        a = base(obs)
        if mode in ('retire','renew') and obs['step'] == 192:
            a['market'] = [['TOY_CASH', 2 if mode=='retire' else 3]]
        return a
    return (candidate, base, base, base)

def payload():
    from factorial_experiment import observations as legal_env_observations
    env = ToyEnv()
    records = []
    for step in range(719):
        obs = legal_env_observations(env)
        acts = [{'farmer': ['PASS'], 'hands': [], 'market': []} for _ in (0, 1)]
        records.extend(({'player': p, 'observation': obs[p], 'action': deepcopy(acts[p])} for p in (0, 1)))
        env.step(acts)
    return {'records': records, 'rewards': [3000.0, 3000.0]}
