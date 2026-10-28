import unittest
import numpy as np
from qhde_qaoa_v05 import DIM, energies_from_scores, metrics, rx_mixer, statevector

class TestQAOA(unittest.TestCase):
    def test_normalization(self):
        e=energies_from_scores(np.r_[np.linspace(.2,2,100),[np.nan]*28])
        for p in ([.3,.8],[.2,.7,.1,.4]):
            self.assertAlmostEqual(float(np.abs(statevector(e,p))@np.abs(statevector(e,p))),1.0,places=10)

    def test_mixer_preserves_norm(self):
        x=np.zeros(DIM,dtype=complex); x[0]=1
        self.assertAlmostEqual(float(np.sum(np.abs(rx_mixer(x,.7))**2)),1.0,places=10)

    def test_uniform_valid_baseline(self):
        scores=np.r_[np.arange(100,dtype=float),np.full(28,np.nan)]
        m=metrics(np.r_[np.full(100,.01),np.zeros(28)],scores)
        self.assertAlmostEqual(m['optimum_probability_given_valid'], .01)
        self.assertAlmostEqual(m['invalid_probability'], 0)

if __name__=='__main__': unittest.main()
