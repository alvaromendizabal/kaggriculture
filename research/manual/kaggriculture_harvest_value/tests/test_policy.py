import ast,unittest
from harvest_policy import transform_call,ACTIVE_DAYS
# Exact expressions copied from the inspected pinned HARVEST blocks. This is a
# fragment harness, not a claim that the full source callback ran locally.
SOURCE='''def __call__(self,obs):
    private=obs['private']
    tile=obs['tile']
    item='MILK'
    animal=80+obs["market"]["prices"][item] * tile["yield_units"] / 10
    crop=tile["yield_units"] * obs["market"]["prices"][tile["crop"]]
    if not tile['watered_today']:
        water=90
    else:
        water=0
    place=obs['market']['prices'][item]*2
    return animal,crop,water,place
'''
class PolicyTests(unittest.TestCase):
    def test_exact_two_calls(self):self.assertEqual(sum(isinstance(n,ast.Call) and getattr(n.func,'id',None)=='__harvest_value' for n in ast.walk(transform_call(SOURCE))),2)
    def test_no_water_edit(self):self.assertIn("not tile['watered_today']",ast.unparse(transform_call(SOURCE)))
    def test_no_place_edit(self):self.assertIn("obs['market']['prices'][item] * 2",ast.unparse(transform_call(SOURCE)))
    def test_missing_pattern_refused(self):
        with self.assertRaises(ValueError):transform_call(SOURCE.replace('tile["crop"]','"TOMATO"'))
    def test_duplicate_pattern_refused(self):
        with self.assertRaises(ValueError):transform_call(SOURCE+ '\n    extra=tile["yield_units"] * obs["market"]["prices"][tile["crop"]]\n')
    def test_null_expression_parity(self):
        a={};b={'__harvest_value':lambda o,p,i,q:o['market']['prices'][i]*q}
        exec(SOURCE,a);exec(compile(transform_call(SOURCE),'<test>','exec'),b)
        o={'private':{},'tile':{'yield_units':4,'crop':'TOMATO','watered_today':False},'market':{'prices':{'MILK':160,'TOMATO':60}}}
        self.assertEqual(a['__call__'](None,o),b['__call__'](None,o))
    def test_helper_receives_same_private(self):
        seen=[];ns={'__harvest_value':lambda o,p,i,q:seen.append(p) or 5};exec(compile(transform_call(SOURCE),'<test>','exec'),ns)
        p={'shed':{}};o={'private':p,'tile':{'yield_units':4,'crop':'TOMATO','watered_today':True},'market':{'prices':{'MILK':160,'TOMATO':60}}};ns['__call__'](None,o);self.assertTrue(all(x is p for x in seen))
    def test_window_fixed(self):self.assertEqual(ACTIVE_DAYS,(20,21))
