import unittest,tempfile,json
from pathlib import Path
import numpy as np
from qhde_batch_optimize_v30 import assert_instance,make_reports
from qhde_optimize_v24 import simulate
class V30Tests(unittest.TestCase):
    def test_v24_statevector_normalized(self):
        p=simulate(np.arange(256)/256,np.array([0.4,0.6]),1)
        self.assertAlmostEqual(p.sum(),1.0,places=12)
    def test_valid_instance(self):
        e=np.linspace(-1,1,256);d={'energies_256':e.tolist(),'scores_256':e.tolist(),'invalid_indices':[],
        'landscape_hash':'h','record_id':'r','optimal_basis_indices':[0],'n_feasible':256}
        a,b=assert_instance({'n_feasible':256,'landscape_hash':'h','record_id':'r'},d)
        self.assertEqual(b.sum(),256)
    def test_reject_bad_optimum(self):
        e=np.linspace(-1,1,256);d={'energies_256':e.tolist(),'scores_256':e.tolist(),'invalid_indices':[],
        'landscape_hash':'h','record_id':'r','optimal_basis_indices':[1],'n_feasible':256}
        with self.assertRaises(ValueError):assert_instance({'n_feasible':256,'landscape_hash':'h','record_id':'r'},d)
if __name__=='__main__':unittest.main()
