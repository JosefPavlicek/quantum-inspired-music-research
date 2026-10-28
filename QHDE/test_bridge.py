import unittest
from unittest.mock import patch
import sys
from types import ModuleType
from types import SimpleNamespace
from qhde_harmonix_bridge import pair_scores

class TestBridge(unittest.TestCase):
    def test_pairs_with_mock_scoring_and_corrected_vocabulary(self):
        candidate=SimpleNamespace
        fake_knowledge=[candidate(symbol='C',roman='I',pitch_classes=frozenset([0,4,7]),function='tonic'), candidate(symbol='G7',roman='V7',pitch_classes=frozenset([2,5,7,11]),function='dominant')]
        def local(m,f,p,c,w):return m+f+p+c
        scorers={'melody_compatibility':lambda s,c,scale,conf:1,
                 'functional_transition':lambda a,b,conf:0,
                 'persistence':lambda a,b,conf:0,
                 'cadential_score':lambda a,b,fin,conf:int(fin and b.roman=='I'),
                 'local_score':local,
                 'segment_has_sounding_notes':lambda s:True}
        fake_pkg=ModuleType('harmonix')
        fake_pkg.__path__=[]
        fake_mod=ModuleType('harmonix.knowledge_candidates')
        fake_mod.generate=lambda *args:fake_knowledge
        with patch.dict(sys.modules, {'harmonix':fake_pkg,'harmonix.knowledge_candidates':fake_mod}):
            r=pair_scores(['s0','s1'],'C','major',set(),{},scoring=scorers,candidate_builder=lambda *x:candidate(symbol=x[0],roman=x[1],pitch_classes=x[2],function=x[3]))
        self.assertEqual(r['pair_count'],4)
        self.assertEqual(r['pairs'][0]['score'],3.0)
        self.assertEqual(r['pairs'][1]['score'],2.0)

if __name__=='__main__':unittest.main()
