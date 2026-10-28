import unittest
from qhde_hooktheory_export import choose_ids

class TestManifest(unittest.TestCase):
    def test_train_only(self):
        doc={'split':'TRAIN','preflight_only':True,'selected':[{'id':'a'},{'id':'b'}]}
        self.assertEqual(choose_ids(doc,1),['a'])
        self.assertEqual(choose_ids(doc,0),['a','b'])
    def test_reject_valid(self):
        with self.assertRaises(ValueError):
            choose_ids({'split':'VALID','preflight_only':True,'selected':[]},0)
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            choose_ids({'split':'TRAIN','preflight_only':True,'selected':[{'id':'x'},{'id':'x'}]},0)

if __name__=='__main__': unittest.main()
