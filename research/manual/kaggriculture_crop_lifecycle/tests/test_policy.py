import ast,unittest
from lifecycle_policy import transform_call,ACTIVE_DAYS
SOURCE='''def __call__(self,obs):
    jobs=[]
    for target,animal in ANIMAL_LAYOUT.items():
        tile=obs['tiles'].get(target)
        if isinstance(tile,dict) and tile.get('kind')=='WEED':
            jobs.append(('ANIMAL_DIG',target))
    for tile in obs['tiles'].values():
        if not tile['watered_today']:
            jobs.append(('WATER',tile['crop']))
    for target,crop in CROP_LAYOUT.items():
        tile=obs['tiles'].get(target)
        remaining=719-obs['step']
        if remaining<=CROPS[crop]['first_yield_day']*24+12:
            continue
        if tile is None:
            jobs.append(('PLANT',target))
        elif isinstance(tile,dict) and tile.get('kind')=='WEED':
            jobs.append(('DIG',target))
    return jobs
'''
class PolicyTests(unittest.TestCase):
    def test_exact_edit_count(self):
        t=transform_call(SOURCE);calls=[getattr(n.func,'id',None) for n in ast.walk(t) if isinstance(n,ast.Call)]
        self.assertEqual(calls.count('__keep_water'),1);self.assertEqual(calls.count('__allow_renewal'),1)
    def test_only_crop_loop_changes(self):
        text=ast.unparse(transform_call(SOURCE));self.assertIn("jobs.append(('ANIMAL_DIG', target))",text)
        self.assertEqual(text.count('__allow_renewal'),1)
    def test_missing_water_predicate_refused(self):
        with self.assertRaises(ValueError):transform_call(SOURCE.replace("not tile['watered_today']","True"))
    def test_missing_crop_loop_refused(self):
        with self.assertRaises(ValueError):transform_call(SOURCE.replace('CROP_LAYOUT.items()','OTHER.items()'))
    def test_null_matches_original(self):
        from helpers import CROPS,plant
        common={'ANIMAL_LAYOUT':{},'CROP_LAYOUT':{(4,4):'TOMATO'},'CROPS':CROPS}
        a=dict(common);b={**common,'__keep_water':lambda t,o:not t['watered_today'],'__allow_renewal':lambda t,o:False}
        exec(SOURCE,a);exec(compile(transform_call(SOURCE),'<test>','exec'),b)
        o={'tiles':{(4,4):plant('TOMATO',0,0)},'step':288};self.assertEqual(a['__call__'](None,o),b['__call__'](None,o))
    def test_renewal_keeps_original_horizon_gate(self):
        from helpers import CROPS,plant
        n={'ANIMAL_LAYOUT':{},'CROP_LAYOUT':{(4,4):'TOMATO'},'CROPS':CROPS,'__keep_water':lambda t,o:False,'__allow_renewal':lambda t,o:True}
        exec(compile(transform_call(SOURCE),'<test>','exec'),n)
        self.assertEqual(n['__call__'](None,{'tiles':{(4,4):plant('TOMATO',0,0)},'step':22*24}),[])
    def test_registered_window(self):self.assertEqual(ACTIVE_DAYS,tuple(range(8,28)))
