import json
import tempfile
import unittest
from pathlib import Path
from qhde_from_scores import read_problem, simulate

class QHDETests(unittest.TestCase):
    def setUp(self):
        self.input=Path(__file__).parent/'data'/'example_scores.json'
    def test_scores(self):
        _,aa,bb,s=read_problem(self.input)
        self.assertEqual(s.shape,(4,4))
        self.assertEqual((aa[2],bb[0]),('G7','Cmaj7'))
        self.assertAlmostEqual(s[2,0],2.7)
    def test_probabilities_and_optimum(self):
        with tempfile.TemporaryDirectory() as d:
            r=simulate(self.input,d,grid=11)
            self.assertEqual(r['n_qubits'],4)
            self.assertAlmostEqual(r['exact_optimum_score'],2.7)
            self.assertGreaterEqual(r['qaoa_expected_score'],r['uniform_expected_score']-1e-10)
            self.assertEqual(len((Path(d)/'candidates.csv').read_text().splitlines()),17)
    def test_reject_invalid_scores(self):
        obj=json.loads(self.input.read_text());obj['pair_scores'][0][0]=float('nan')
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'bad.json'; f.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):read_problem(f)
if __name__=='__main__':unittest.main()
