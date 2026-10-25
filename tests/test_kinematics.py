import unittest,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from core import *
class KinematicsTests(unittest.TestCase):
    def test_inverse_has_two_verified_solutions(self):
        result=synthesize(300,250,40,1.2);self.assertEqual(len(result['candidates']),2)
        for c in result['candidates']:
            f=FourBar(**{k:c[k] for k in ('ground','crank','coupler','rocker')})
            e=f.extrema();self.assertAlmostEqual(e['swing_deg'],40,places=9);self.assertAlmostEqual(e['K'],1.2,places=10)
            self.assertGreater(f.full_turn_margin(),0)
    def test_rounded_prior_lengths_conflict(self):
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            parameters({'lengths':{'ground':300,'crank':65.6,'coupler':390.6,'rocker':250},'design':{'swing_deg':40,'K':1.2}})
    def test_design_requires_choice(self):
        with self.assertRaisesRegex(ValueError,'Multiple'):
            parameters({'lengths':{'ground':300,'rocker':250},'design':{'swing_deg':40,'K':1.2}})
    def test_full_turn_and_mirror(self):
        f=FourBar(300,83.60514904142842,151.17292022893315,250);g=FourBar(f.ground,f.crank,f.coupler,f.rocker,-1)
        for i in range(721):
            p=f.pose(i*.5);r=g.pose(-i*.5)
            self.assertLess(p['closure_error_mm'],1e-9);self.assertAlmostEqual(p['C'][0],r['C'][0],places=8);self.assertAlmostEqual(p['C'][1],-r['C'][1],places=8)
    def test_continuity_two_rotations(self):
        f=FourBar(300,65.63218169655732,390.6459004035889,250)
        rows=simulate(f,{'rpm':50,'duration_s':2.4,'dt_s':.01,'initial_deg':355,'direction':1})
        self.assertEqual(len(rows),241);self.assertAlmostEqual(rows[-1]['crank_deg']-rows[0]['crank_deg'],720)
        self.assertLess(max(abs(y['rocker_deg']-x['rocker_deg']) for x,y in zip(rows,rows[1:])),10)
    def test_reverse_direction_velocity(self):
        f=FourBar(300,83.60514904142842,151.17292022893315,250)
        rows=simulate(f,{'rpm':20,'duration_s':1.,'dt_s':.01,'initial_deg':45,'direction':-1})
        self.assertTrue(all(abs(x['crank_velocity_deg_s']+120)<1e-8 for x in rows))
    def test_infeasible_and_toggle_rejected(self):
        for lengths in [{'ground':300,'crank':50,'coupler':50,'rocker':50},{'ground':100,'crank':100,'coupler':100,'rocker':100}]:
            with self.assertRaises(ValueError):parameters({'lengths':lengths})
    def test_invalid_values(self):
        for x in (-1,0,float('nan'),float('inf')):
            with self.assertRaises(ValueError):FourBar(x,2,3,4)
    def test_unimplemented_mechanism(self):
        with self.assertRaises(NotImplementedError):parameters({'mechanism_type':'gear'})
    def test_underconstrained(self):
        with self.assertRaisesRegex(ValueError,'Missing'):parameters({'lengths':{'ground':300}})
    def test_other_scale_and_double_crank(self):
        # A shortest ground link yields a double-crank inversion, not the acceptance crank-rocker.
        f=FourBar(20,50,40,45);audit=f.audit();self.assertTrue(audit['full_turn_possible'])
        rows=simulate(f,{'rpm':12,'duration_s':10,'dt_s':.01,'initial_deg':20,'direction':1})
        self.assertGreater(abs(rows[-1]['rocker_deg']-rows[0]['rocker_deg']),360)
if __name__=='__main__':unittest.main()
