import unittest
from qhde_music_complexity_v16 import chord_label, evaluate_record

class SchemaTests(unittest.TestCase):
    def test_major_minor(self):
        a={'onset':0,'offset':3,'root_pitch_class':0,'root_position_intervals':[4,3],'inversion':0}
        b={'onset':3,'offset':8,'root_pitch_class':7,'root_position_intervals':[3,4],'inversion':0}
        self.assertEqual(chord_label(a),'pc0:intervals(4,3):inv0')
        self.assertNotEqual(chord_label(a),chord_label(b))
    def test_unusual_intervals(self):
        c={'onset':8,'offset':11,'root_pitch_class':5,'root_position_intervals':[5,2,7],'inversion':0}
        self.assertIsNotNone(chord_label(c))
    def test_invalid(self):
        c={'onset':8,'offset':8,'root_pitch_class':5,'root_position_intervals':[4,3],'inversion':0}
        self.assertIsNone(chord_label(c))
    def test_complete(self):
        c=lambda on,off,root,ints:{'onset':on,'offset':off,'root_pitch_class':root,'root_position_intervals':ints,'inversion':0}
        r=evaluate_record({'annotations':{'harmony':[c(0,3,0,[4,3]),c(3,8,7,[3,4]),c(8,11,5,[5,2,7])]}})
        self.assertEqual(r['status'],'ok')
        self.assertEqual(r['n_unique_chords'],3)
if __name__=='__main__':unittest.main()
