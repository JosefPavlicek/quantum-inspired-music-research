import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from qhde_expand_v29 import split_for_id,canonical_landscape
class TestExpansion(unittest.TestCase):
 def test_split_deterministic(self):self.assertEqual(split_for_id('abc'),split_for_id('abc'))
 def test_split_no_outside(self):self.assertIn(split_for_id('abc'),('internal_train','internal_validation'))
 def test_canonical_affine(self):
  a=list(range(256));b=[2*v+5 for v in a]
  self.assertEqual(canonical_landscape(a),canonical_landscape(b))
 def test_canonical_invalid(self):
  with self.assertRaises(ValueError):canonical_landscape([1,2])
if __name__=='__main__':unittest.main()
