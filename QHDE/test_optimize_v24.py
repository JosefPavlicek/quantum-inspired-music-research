import unittest
import numpy as np
from qhde_optimize_v24 import simulate, optimize, get_optimal

class Tests(unittest.TestCase):
    def test_uniform_at_zero(self):
        e=np.linspace(-1,1,256)
        p=simulate(e,np.zeros(2),1)
        self.assertLess(np.max(np.abs(p-1/256)),1e-12)
    def test_normalization(self):
        e=np.sin(np.arange(256))
        for d in (1,2,3):
            p=simulate(e,np.linspace(0.1,1.4,d*2),d)
            self.assertTrue(np.isfinite(p).all())
            self.assertAlmostEqual(p.sum(),1,places=12)
    def test_feasible_optimum(self):
        e=np.arange(256.)
        f=np.zeros(256,bool);f[[4,6]]=True
        self.assertEqual(list(get_optimal(e,f)),[4])
    def test_optimizer_improves_uniform(self):
        e=np.ones(256);e[0]=0
        r=optimize(e,np.ones(256,bool),1,starts=2,maxiter=50)
        self.assertLessEqual(r['expected_energy'],np.mean(e)+1e-8)
    def test_physical_vector(self):
        try:
            from qiskit.quantum_info import Statevector
        except ImportError:
            self.skipTest("Qiskit not installed in this environment; required in Codespaces")
        from qhde_structured_qaoa_v23 import make_circuit
        e=np.cos(np.arange(256)*0.05)
        for p in (1,2):
            x=np.array([0.2]*p+[0.4]*p)
            qc=make_circuit(e,p,x[:p],x[p:])
            measured=np.abs(Statevector.from_instruction(qc).data)**2
            self.assertLess(np.max(np.abs(simulate(e,x,p)-measured)),1e-10)
if __name__=='__main__':unittest.main()
