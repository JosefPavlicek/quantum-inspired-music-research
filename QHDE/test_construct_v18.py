import unittest
import numpy as np
from qhde_construct_v18 import reduce_fixed,matrix_from_score

class ConstructionTests(unittest.TestCase):
    def test_fixed_selection_independent_of_scores(self):
        mat=np.arange(100,dtype=float).reshape(10,10)
        r=reduce_fixed(mat)
        self.assertEqual(r['a_indices'],[0,2,4,6]);self.assertFalse(r['full_optimum_represented'])
        self.assertEqual(len(r['scores_16']),16)
    def test_full_optimum_can_be_represented(self):
        mat=np.zeros((10,10));mat[2,4]=10
        r=reduce_fixed(mat);self.assertTrue(r['full_optimum_represented']);self.assertEqual(r['optimal_basis_indices'],[6])
    def test_reject_incomplete(self):
        d={'candidate_variant':'corrected','candidate_count':10,'pairs':[{'a_index':0,'b_index':0,'score':1}]}
        with self.assertRaises(ValueError):matrix_from_score(d)
    def test_reject_cherry_picked_index_duplication(self):
        with self.assertRaises(ValueError):reduce_fixed(np.zeros((10,10)),[0,0,1,2])
if __name__=='__main__':unittest.main()
