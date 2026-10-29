import unittest
import numpy as np
from qhde_ibm_v25 import wilson,check_map
class Tests(unittest.TestCase):
 def test_wilson(self):
  a,b=wilson(50,100);self.assertLess(a,.5);self.assertGreater(b,.5)
 def test_wilson_bounds(self):
  for n in (10,100,1024):
   for k in (0,n):
    a,b=wilson(k,n);self.assertGreaterEqual(a,-1e-12);self.assertLessEqual(b,1+1e-12)
 def test_map_requires_layout(self):
  class C: name='test';layout=None
  with self.assertRaises(ValueError):check_map(C())
 def test_simulation_normalized(self):
  from qhde_optimize_v24 import simulate
  energy=np.linspace(-1,0,256)
  for p in (1,2,3):
   d=simulate(energy,np.array([.1]*p+[.2]*p),p)
   self.assertAlmostEqual(d.sum(),1,places=9)
if __name__=='__main__':unittest.main()
