import unittest, json, os
from pathlib import Path
from qhde_depth_hardware_v33 import choose,read_sources,source_checksums

class TestV33(unittest.TestCase):
    def setUp(self):
        self.instances=Path(os.environ.get('QHDE_V33_INSTANCES_DIR','QHDE/results/expanded_v29_full'))
        self.results=Path(os.environ.get('QHDE_V33_RESULTS_DIR','QHDE/results/optimize_v30_full'))
        self.inst,self.manifest,self.runs=read_sources(self.instances,self.results)
    def test_selection(self):
        chosen=choose(self.manifest,None,6)
        self.assertEqual(len(chosen),24)
        self.assertEqual(len({r['landscape_hash'] for r in chosen}),24)
        self.assertEqual(sorted(sum(r['stratum']==st for r in chosen) for st in {r['stratum'] for r in chosen}),[6]*4)
        self.assertTrue(all(r['partition']=='internal_train' and r['n_feasible']==256 for r in chosen))
    def test_optimization_matches(self):
        self.assertEqual(len(self.runs),400)
        for row in choose(self.manifest,None,6):
            self.assertTrue((self.inst/row['file']).is_file())
            self.assertEqual(self.runs[row['record_id']]['landscape_hash'],row['landscape_hash'])
            for depth in (1,2,3):
                self.assertEqual(len(self.runs[row['record_id']]['models'][f'p{depth}']['params']),2*depth)
    def test_source_hashes(self):
        hashes=source_checksums(self.instances,self.results)
        self.assertEqual(len(hashes['manifest_sha256']),64)
        self.assertEqual(len(hashes['runs_sha256']),64)

if __name__=='__main__':unittest.main()
