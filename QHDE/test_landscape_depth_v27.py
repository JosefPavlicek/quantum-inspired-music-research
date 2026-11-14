import sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from qhde_landscape_depth_v27 import walsh,landscape_metrics,grouping,loo_ridge,bh
class TestV27(unittest.TestCase):
    def test_walsh_parseval(self):
        x=np.random.default_rng(4).normal(size=256)
        self.assertAlmostEqual(float(np.var(x)),float(np.sum(walsh(x)[1:]**2)),places=11)
    def test_local_chain(self):
        e=np.arange(256,dtype=float);v=landscape_metrics(e)
        self.assertEqual(v['nonlocal_terms_recomputed'],0)
    def test_group_affine(self):
        e=np.arange(256,dtype=float)
        rows=[{'record_id':'a','_energies':e},{'record_id':'b','_energies':4*e+7},
              {'record_id':'c','_energies':e[::-1]}]
        g=grouping(rows)
        self.assertEqual(len(g),2)
        self.assertEqual(g[0],['a','b'])
    def test_bh(self):
        self.assertTrue(np.allclose(bh([0.01,0.02,0.2]),[0.03,0.03,0.2]))
    def test_loo(self):
        rows=[{'x':float(i),'y':float(i)/10} for i in range(8)]
        d=loo_ridge(rows,('x',),'y')
        self.assertLess(d['loo_mae_pp'],d['baseline_loo_mae_pp'])
if __name__=='__main__':unittest.main()
