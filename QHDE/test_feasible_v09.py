import unittest
import numpy as np
from qhde_feasible_v09 import feasible_initial,projector_mixer,statevector,normalized_energies,stats

class TestFeasible(unittest.TestCase):
    def test_initialization(self):
        psi=feasible_initial()
        self.assertAlmostEqual(float(np.vdot(psi,psi).real),1.)
        self.assertEqual(np.count_nonzero(psi[100:]),0)
    def test_feasible_and_norm_after_layers(self):
        energy=normalized_energies(np.linspace(.2,1.2,100))
        for params in ([.3,.4],[.3,.4,.7,.8]):
            psi=statevector(energy,params)
            self.assertAlmostEqual(float(np.vdot(psi,psi).real),1.,places=12)
            self.assertLess(float(np.sum(abs(psi[100:])**2)),1e-22)
    def test_mixer_is_unitary_on_generic_state(self):
        rng=np.random.default_rng(2)
        v=rng.normal(size=128)+1j*rng.normal(size=128)
        v=v/np.linalg.norm(v)
        out=projector_mixer(v,.7)
        self.assertAlmostEqual(float(np.linalg.norm(out)),1.,places=12)
    def test_metrics_uniform(self):
        scores=np.arange(100,dtype=float)
        m=stats(feasible_initial(),scores)
        self.assertAlmostEqual(m['optimum_probability'],.01)
        self.assertAlmostEqual(m['invalid_probability'],0)

if __name__=='__main__':unittest.main()
