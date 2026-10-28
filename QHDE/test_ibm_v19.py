import unittest
import numpy as np
from qhde_ibm_v19 import canonical_energy, make_circuit, wilson

class Tests(unittest.TestCase):
    def test_energy_normalization(self):
        x=canonical_energy(np.arange(16.))
        self.assertAlmostEqual(float(x[0]),0)
        self.assertAlmostEqual(float(x[-1]),-1)
    def test_equal_scores_rejected(self):
        with self.assertRaises(ValueError):canonical_energy(np.ones(16))
    def test_params_p3(self):
        from qiskit.quantum_info import Statevector
        from qhde_hardware_v10 import np_state
        energy=canonical_energy(np.linspace(1,2,16))
        pars=np.array([.3,.6,1.2,2.1,0.7,1.5])
        qc=make_circuit(energy,pars,measure=False)
        self.assertLess(float(np.max(np.abs(np.abs(Statevector.from_instruction(qc).data)**2-abs(np_state(energy,pars))**2))),1e-10)
    def test_wilson(self):
        a,b=wilson(75,1024)
        self.assertLess(a,75/1024);self.assertGreater(b,75/1024)
    def test_circuit_measure(self):
        qc=make_circuit(canonical_energy(np.arange(16)),np.ones(6),name='test')
        self.assertEqual(qc.num_clbits,4)
        self.assertEqual(qc.count_ops()['measure'],4)
if __name__=='__main__':unittest.main()
