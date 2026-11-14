import unittest
import numpy as np
from qhde_local_complexity_v28 import scores_from_factors,local_features,bh,loo_mae

class TestV28(unittest.TestCase):
 def base(self):
  u=[[0.,1.,2.,3.]]*4
  t=np.zeros((3,4,4)).tolist()
  return {'unary_scores':u,'transition_scores':t,'scores_256':scores_from_factors(u,t).tolist(),'n_feasible':256}
 def test_factorization(self):
  x=self.base(); self.assertEqual(local_features(x)['score_reconstruction_max_error'],0)
 def test_zero_coupling(self):
  self.assertAlmostEqual(local_features(self.base())['coupling_rms'],0)
 def test_double_centered_row_col(self):
  x=self.base();t=np.asarray(x['transition_scores']);t[0,:,:]=np.arange(4)[:,None]+2*np.arange(4)[None,:]
  x['transition_scores']=t.tolist();x['scores_256']=scores_from_factors(x['unary_scores'],t).tolist()
  self.assertLess(local_features(x)['coupling_rms'],1e-12)
 def test_interaction(self):
  x=self.base();t=np.asarray(x['transition_scores']);t[0,0,0]=10
  x['transition_scores']=t.tolist();x['scores_256']=scores_from_factors(x['unary_scores'],t).tolist()
  self.assertGreater(local_features(x)['coupling_rms'],0)
 def test_score_guard(self):
  x=self.base();x['scores_256'][0]+=1
  with self.assertRaises(ValueError):local_features(x)
 def test_bh(self):self.assertEqual(len(bh([0.01,0.03,0.5])),3)
 def test_loo(self):
  rows=[{'a':float(i),'b':float(i*i),'y':float(i%3)} for i in range(12)]
  x=loo_mae(rows,['a','b'],'y');self.assertGreaterEqual(x['mae_pp'],0)
if __name__=='__main__':unittest.main()
