import unittest
import numpy as np
from qhde_hardware_v10 import build_problem,np_state,optimize,make_circuit

class TestV10(unittest.TestCase):
    def setUp(self):
        self.data={'candidate_variant':'corrected','candidate_count':10,
                   'pairs':[{'a_index':i,'b_index':j,'score':float(i*0.2+j*0.07+0.01*i*j)}
                            for i in range(10) for j in range(10)]}
    def test_selection_deterministic(self):
        a=build_problem(self.data);b=build_problem(self.data)
        self.assertEqual(a['a_indices'],b['a_indices'])
        self.assertEqual(a['b_indices'],b['b_indices'])
        self.assertEqual(a['energies'].shape,(16,))
    def test_probabilities(self):
        e=build_problem(self.data)['energies']
        for p in ([0.4,0.3],[0.4,0.3,0.5,0.2]):
            self.assertAlmostEqual(float(np.abs(np_state(e,p))@np.abs(np_state(e,p))),1,places=11)
    def test_qiskit_equivalence(self):
        try:
            from qiskit.quantum_info import Statevector
        except ImportError:
            self.skipTest("Qiskit not installed in local packaging environment")
        e=build_problem(self.data)['energies']
        for params in ([.4,.3],[.4,.3,.6,.2]):
            self.assertLess(np.max(np.abs(Statevector.from_instruction(make_circuit(e,params)).data - np_state(e,params))),1e-10)
    def test_optimization_reproducible(self):
        e=build_problem(self.data)['energies']
        a,v=optimize(e,1,seed=23,starts=5);b,w=optimize(e,1,seed=23,starts=5)
        self.assertTrue(np.array_equal(a,b));self.assertEqual(v,w)

if __name__=='__main__':unittest.main()
