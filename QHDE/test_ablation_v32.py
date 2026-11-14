import unittest,numpy as np
from qhde_ablation_v32 import calc_scores,dp_chain,shuffle_pairs,local_choice,index_of
class TestV32(unittest.TestCase):
 def test_zero(self):
  u=np.zeros((4,4));t=np.zeros((3,4,4));self.assertTrue(np.all(calc_scores(u,t)==0))
 def test_dp(self):
  rng=np.random.default_rng(2);u=rng.normal(size=(4,4));t=rng.normal(size=(3,4,4));score=calc_scores(u,t);v,idx=dp_chain(u,t);self.assertAlmostEqual(v,max(score));self.assertAlmostEqual(score[idx],v)
 def test_shuffle_preserves_values(self):
  t=np.arange(48).reshape(3,4,4);s=shuffle_pairs(t,12)
  for j in range(3):self.assertEqual(sorted(t[j].ravel()),sorted(s[j].ravel()))
 def test_unary(self):
  u=np.zeros((4,4));u[0,3]=5;u[1,1]=6;self.assertEqual(index_of(local_choice(u)),3*64+1*16)
if __name__=='__main__':unittest.main()
