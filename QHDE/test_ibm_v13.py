import json
import tempfile
import unittest
from pathlib import Path
from qhde_ibm_v13 import wilson, analyze

class TestV13(unittest.TestCase):
    def test_wilson_bounds(self):
        lo,hi=wilson(141,1024)
        self.assertLess(lo,141/1024)
        self.assertGreater(hi,141/1024)
        self.assertEqual(wilson(0,0),[None,None])
    def test_analysis_mock_without_ibm(self):
        class Args: pass
        with tempfile.TemporaryDirectory() as d:
            a=Args();a.out=d
            records=[];counts=[];names=[]
            for i in range(5):
                records.append({'score_file':f'scores_{i:03d}.json','record_id':f'record{i}',
                  'problem':{'optimal_basis_indices':[2],'full_optimum_represented':True,
                             'ideal_uniform_optimum_probability':1/16},
                  'p1':{'ideal_optimum_probability':0.2},'p2':{'ideal_optimum_probability':0.3}})
                counts.extend([{'0010':1,'0000':15},{'0010':4,'0000':12},{'0010':8,'0000':8}])
                names.extend([f'r{i}_uniform',f'r{i}_p1',f'r{i}_p2'])
            Path(d,'preparation.json').write_text(json.dumps({'shots':16,'records':records,'circuits_order':names}))
            Path(d,'raw_results.json').write_text(json.dumps({'job_id':'test','backend':'mock',
                                         'counts_ordered':counts,'circuits_order':names}))
            analyze(a)
            out=json.loads(Path(d,'analysis.json').read_text())
            self.assertEqual(len(out['records']),5)
            self.assertEqual(out['records'][0]['measurements'][1]['hits'],4)
            self.assertEqual(out['records'][0]['qaoa_vs_uniform_p2_delta'],7/16)
if __name__=='__main__':unittest.main()
