import unittest
import numpy as np
from qiskit.quantum_info import Statevector
from qhde_structured_v08 import (walsh_coefficients,reconstruct,select_coeffs,
    qaoa_circuit, reference_qaoa, phase_aligned_error, energies_from_export)
class TestStructuredV08(unittest.TestCase):
    def test_walsh_roundtrip(self):
        rng=np.random.default_rng(42)
        e=rng.normal(size=128)
        np.testing.assert_allclose(reconstruct(walsh_coefficients(e)),e,atol=1e-12)
    def test_exact_circuit(self):
        rng=np.random.default_rng(42)
        e=rng.normal(size=128)
        c=walsh_coefficients(e)
        for gammas,betas in [([0.7],[0.4]),([0.5,-0.3],[0.2,0.1])]:
            a=Statevector.from_instruction(reference_qaoa(e,gammas,betas)).data
            b=Statevector.from_instruction(qaoa_circuit(c,gammas,betas)).data
            self.assertLess(phase_aligned_error(a,b),1e-10)
    def test_valid_encoding(self):
        data={'candidate_count':10,'pairs':[{'a_index':i,'b_index':j,'score':i+j/10} for i in range(10) for j in range(10)]}
        s,e,v=energies_from_export(data)
        self.assertEqual(len(e),128)
        self.assertEqual(s[10],1.0)
        self.assertTrue(np.all(s[100:]<s[:100].min()))
    def test_truncation(self):
        e=np.arange(128,dtype=float)/100
        c=walsh_coefficients(e)
        s=select_coeffs(c,max_terms=3)
        self.assertLessEqual(np.count_nonzero(abs(s[1:])>1e-12),3)
if __name__=='__main__':unittest.main()
