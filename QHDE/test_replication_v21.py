import unittest
from qhde_replication_v21 import permutation, calculate

class TestV21(unittest.TestCase):
    def test_permutation(self):
        p=permutation();self.assertEqual(sorted(p),list(range(64)))
        self.assertEqual(p,permutation())
        self.assertNotEqual(p,list(range(64)))
    def test_synthetic_alignment(self):
        import numpy as np
        names=[f'clip_{i//4:02d}_{("uniform","p1","p2","p3")[i%4]}' for i in range(64)]
        parent={'records':[]};prior={'records':[]}
        for i in range(16):
            parent['records'].append({'record_id':str(i),'stratum':'A','optimal_basis_indices':[0],
                'scores_16':[1.0]+[0.0]*15,'music_features':{}})
            prior['records'].append({'record_id':str(i),'results':[{'model':m,'optimum_probability':0.125,
                'expected_harmonic_score':0.125,'ideal_optimum_probability':0.0625} for m in ('uniform','p1','p2','p3')]})
        p=permutation(21)
        # Reorder results in the new order. Each old result deliberately differs by PUB index.
        old_counts=[{'0000':(i+1),'1111':1024-i-1} for i in range(64)]
        raw={'circuits_sha256':'x','counts_reordered':[old_counts[j] for j in p]}
        prep={'reordered_circuits_sha256':'x','permutation_new_to_original':p,'shots':1024,'backend':'x'}
        report=calculate(prep,raw,parent,prior)
        self.assertEqual(report['records'][0]['results'][0]['replicate_hits'],1)
        self.assertEqual(report['records'][15]['results'][3]['replicate_hits'],64)

if __name__=='__main__':unittest.main()
