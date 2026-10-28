import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from qhde_complexity_selection_v17 import conditional_entropy, extract_labels, analyze, select

class TestV17(unittest.TestCase):
    def test_deterministic_sequence(self):
        self.assertEqual(conditional_entropy(['A','B','A','B']),0.0)
    def test_variable_successor(self):
        self.assertGreater(conditional_entropy(['A','B','A','C']),0.0)
    def test_schema(self):
        rec={'annotations':{'harmony':[{'onset':0,'offset':1,'root_pitch_class':0,'root_position_intervals':[4,3],'inversion':0}, {'onset':1,'offset':2,'root_pitch_class':7,'root_position_intervals':[3,4],'inversion':0}]}}
        self.assertEqual(analyze(rec,'x')['n_chords'],2)
    def test_overlap_rejected(self):
        rec={'annotations':{'harmony':[{'onset':0,'offset':2,'root_pitch_class':0,'root_position_intervals':[4,3],'inversion':0}, {'onset':1,'offset':3,'root_pitch_class':7,'root_position_intervals':[3,4],'inversion':0}]}}
        self.assertIsNone(extract_labels(rec))
    def test_stable_blind_selection(self):
        rows=[]
        for i in range(16):
            rows.append({'record_id':f'id{i}','status':'ok','n_chords':12,'conditional_transition_entropy_bits':i/4,'repeated_bigram_rate':(i%4)/4})
        a,m=select(rows,2,8,{'id0'});b,_=select(rows,2,8,{'id0'})
        self.assertEqual(a,b)
        self.assertNotIn('id0',[r['record_id'] for r in a])
        self.assertLessEqual(len(a),8)
if __name__=='__main__':unittest.main()
