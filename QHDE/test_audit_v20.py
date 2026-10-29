import unittest
from qhde_audit_v20 import fp, spearman, run
class AuditTests(unittest.TestCase):
 def test_additive_shift(self):self.assertEqual(fp([1,2,3]),fp([3,4,5]))
 def test_affine(self):self.assertEqual(fp([1,2,3],True),fp([10,12,14],True))
 def test_spearman(self):self.assertAlmostEqual(spearman([1,2,3],[3,2,1]),-1)
 def test_zero_variance(self):self.assertIsNone(spearman([1,1,1],[1,2,3]))
if __name__=='__main__':unittest.main()
