import unittest
import numpy as np
from qhde_audit_v26 import paired_test,ci_bootstrap,spearman
class TestAudit(unittest.TestCase):
    def test_signflip_all_positive(self): self.assertAlmostEqual(paired_test([1,2,3]),.25)
    def test_signflip_null(self): self.assertAlmostEqual(paired_test([0,0]),1.)
    def test_bootstrap_constant(self): self.assertEqual(ci_bootstrap([2,2,2]),[2.,2.])
    def test_spearman(self): self.assertAlmostEqual(spearman([1,2,3],[3,2,1]),-1.)
if __name__=='__main__':unittest.main()
