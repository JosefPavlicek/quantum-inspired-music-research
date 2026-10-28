import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from qhde_music_complexity_v16 import evaluate_record, entropy, select_train
class Tests(unittest.TestCase):
    def test_entropy(self): self.assertAlmostEqual(entropy(['C','G','C','G']),1.0)
    def test_annotation(self):
        x=evaluate_record({'annotations':{'harmony':[{'symbol':'C'},{'symbol':'G7'},{'symbol':'C'}]}})
        self.assertEqual(x['status'],'ok');self.assertEqual(x['n_chords'],3)
    def test_skip_incomplete(self):
        x=evaluate_record({'harmony':[{'symbol':'C'},{'missing':'F'}]})
        self.assertEqual(x['status'],'incomplete_annotations')
    def test_dont_use_melody(self):
        self.assertEqual(evaluate_record({'melody':[{'symbol':'C'},{'symbol':'D'}]})['status'],'unsupported_schema')
    def test_manifest_guard(self):
        with self.assertRaises(ValueError):select_train({'split':'TEST','preflight_only':True,'selected':[]},5)
if __name__=='__main__':unittest.main()
