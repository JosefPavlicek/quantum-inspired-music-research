import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from qhde_four_segments_v22 import normalized_energy,four_scores

class Dummy:
    def __init__(self,j):self.symbol=str(j);self.roman=str(j);self.function='tonic';self.pitch_classes={j}
class Key:tonic='C';mode='major'
class Tests(unittest.TestCase):
    def test_energy(self):
        p={'scores_256':list(range(256)),'invalid_indices':[]}
        e,o=normalized_energy(p)
        self.assertEqual(o,[255]);self.assertAlmostEqual(e[255],-1);self.assertAlmostEqual(e[0],0)
    def test_invalid_energy(self):
        p={'scores_256':list(range(255))+[None]}
        e,o=normalized_energy(p)
        self.assertEqual(o,[254]);self.assertEqual(e[255],2)
    def test_four_consecutive_links(self):
        def local(m,t,p,c,w):return m+t+p+c
        s={'local_score':local,'melody_compatibility':lambda seg,ch,scale,conf:float(seg+int(ch.symbol)),
          'functional_transition':lambda a,b,conf:0 if a is None else 10*int(a.symbol)+int(b.symbol),
          'persistence':lambda a,b,conf:0,'cadential_score':lambda a,b,last,conf:0,
          'segment_has_sounding_notes':lambda seg:True}
        env={'ChordCandidate':lambda *x:Dummy(int(x[0])), 'generate':lambda *args:[Dummy(i) for i in range(10)],
             'scoring':s,'config':{}}
        result=four_scores([0,1,2,3],Key(),set(),env)
        self.assertEqual(len(result['scores_256']),256)
        # chain 0 -> 2 -> 4 -> 6: base note+chord contributions plus three transitions
        ix=0*64+1*16+2*4+3
        expected=sum([0+0,1+2,2+4,3+6])+((0*10+2)+(2*10+4)+(4*10+6))
        self.assertAlmostEqual(result['scores_256'][ix],expected)
if __name__=='__main__':unittest.main()
