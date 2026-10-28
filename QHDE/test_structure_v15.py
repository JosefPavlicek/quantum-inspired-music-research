import unittest, importlib.util
from pathlib import Path
p=Path(__file__).with_name('qhde_structure_v15.py')
spec=importlib.util.spec_from_file_location('qhde_structure_v15',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class TestLandscape(unittest.TestCase):
    def test_entropy(self):
        self.assertAlmostEqual(m.shannon([.5,.5]),1.)
    def test_correlation(self):
        self.assertAlmostEqual(m.pearson([1,2,3],[3,6,9]),1.)
    def test_correlation_constant(self):
        self.assertIsNone(m.pearson([1,1,1],[1,2,3]))
    def test_real_data(self):
        original=Path('/mnt/data/audit.json')
        if original.exists():
            import json
            d=json.loads(original.read_text());self.assertEqual(len(d['records']),5)
            self.assertEqual(m.audit_record(d['records'][-1])['optimum_count'],1)
if __name__=='__main__':unittest.main()
