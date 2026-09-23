from fractions import Fraction
from emh.model import NoteEvent
from emh.key_detection import detect_key

def n(pc, dur=1, i=0):
    return NoteEvent(str(pc),pc,Fraction(i),Fraction(dur),1,Fraction(1),1.0,False)

def melody(pcs):
    return [n(pc,dur,i) for i,(pc,dur) in enumerate(pcs)]

def test_detects_c_major_profile():
    # C-major triad/scale material with tonic and dominant emphasized.
    r=detect_key(melody([(0,8),(7,6),(4,5),(5,3),(2,3),(9,2),(11,1)]))
    assert (r.tonic,r.mode)==("C","major")
    assert len(r.ranking)==24

def test_detects_e_major_profile():
    r=detect_key(melody([(4,8),(11,6),(8,5),(9,3),(6,3),(1,2),(3,1)]))
    assert (r.tonic,r.mode)==("E","major")

def test_detects_a_minor_profile():
    r=detect_key(melody([(9,8),(4,5),(0,5),(2,3),(5,3),(7,2),(11,1)]))
    assert (r.tonic,r.mode)==("A","minor")

def test_rests_do_not_affect_detection():
    notes=melody([(0,8),(7,6),(4,5),(5,3),(2,3),(9,2),(11,1)])
    notes.append(NoteEvent(None,None,Fraction(20),Fraction(16),2,Fraction(1),1.0,True))
    assert detect_key(notes).name=="C major"
