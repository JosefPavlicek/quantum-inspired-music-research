import unittest,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from qhde_structured_qaoa_v23 import walsh_coefficients,reconstruct,analyze,support_properties
class TestV23(unittest.TestCase):
    def test_roundtrip(self):
        a=np.random.default_rng(42).normal(size=256)
        self.assertLess(np.max(np.abs(reconstruct(walsh_coefficients(a))-a)),1e-12)
    def test_exact_chain_terms(self):
        e=np.array([((i>>0)&1)*0.2+((i>>2)&1)*0.3 + ((i>>0)&1)*((i>>2)&1)*0.5 for i in range(256)])
        _,_,higher,err=analyze(e)
        self.assertEqual(len(higher),0);self.assertLess(err,1e-12)
    def test_distant_dependency(self):
        e=np.array([((i>>0)&1)*((i>>7)&1) for i in range(256)])
        _,_,higher,_=analyze(e)
        self.assertGreater(len(higher),0)
    def test_support(self):
        self.assertEqual(support_properties(0b10000001),(2,2,3))
if __name__=='__main__':unittest.main()
