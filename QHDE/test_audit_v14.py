"""Offline unit tests: python -m unittest discover -s QHDE -p test_audit_v14.py -v"""
import unittest
import numpy as np
from qhde_audit_v14 import wilson, parse_counts, delta, classical_baselines, measured_row

class AuditV14Tests(unittest.TestCase):
    def test_counts_endianness_convention(self):
        x=parse_counts({'0010':7,'1111':2})
        self.assertEqual(int(x[2]),7)
        self.assertEqual(int(x[15]),2)
        self.assertEqual(int(x.sum()),9)
    def test_bad_counts_rejected(self):
        with self.assertRaises(ValueError):parse_counts({'101':2})
    def test_wilson_boundaries(self):
        lo,hi=wilson(0,1024)
        self.assertEqual(lo,0.0)
        self.assertTrue(0 < hi < .01)
        lo,hi=wilson(1024,1024)
        self.assertEqual(hi,1.0)
        self.assertTrue(.99 < lo < 1)
    def test_exact_baseline(self):
        scores=np.arange(16,dtype=float)
        b=classical_baselines(scores,[15])
        self.assertEqual(b['exact_enumeration']['candidate_evaluations'],16)
        self.assertAlmostEqual(b['random_with_replacement'][0]['expected_best_score'],7.5)
        self.assertAlmostEqual(b['random_with_replacement'][0]['probability_at_least_one_optimum'],1/16)
    def test_score_and_delta(self):
        a=measured_row(np.full(16,64),np.arange(16),[15],'uniform',1/16)
        b=measured_row(np.array([0]*15+[1024]),np.arange(16),[15],'p1',1.)
        self.assertAlmostEqual(a['expected_harmonic_score'],7.5)
        self.assertAlmostEqual(b['expected_harmonic_score'],15)
        self.assertAlmostEqual(delta(a,b)['delta_percentage_points'],93.75)

if __name__=='__main__':unittest.main()
