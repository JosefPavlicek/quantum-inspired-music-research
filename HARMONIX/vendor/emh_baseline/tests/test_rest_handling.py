from fractions import Fraction
from emh.model import NoteEvent,HarmonicSegment
from emh.harmony import generate_candidates
from emh.optimizer import optimize

SCALE={0,2,4,5,7,9,11}
C=generate_candidates("C")
def sounding(i,pcs):
 n=[NoteEvent(str(p),p,Fraction(j),Fraction(1),i+1,Fraction(j+1),1.0,False) for j,p in enumerate(pcs)]
 return HarmonicSegment(i,i+1,Fraction(1),Fraction(2),n)
def silent(i):
 n=[NoteEvent(None,None,Fraction(0),Fraction(2),i+1,Fraction(1),1.0,True)]
 return HarmonicSegment(i,i+1,Fraction(1),Fraction(2),n)

def test_rest_only_segment_carries_previous_chord():
 d=optimize([sounding(0,[0,4,7]),silent(1),sounding(2,[5,9,0])],C,SCALE)
 assert d[1].selected.roman==d[0].selected.roman

def test_two_silent_segments_do_not_create_harmonic_motion():
 d=optimize([sounding(0,[7,11,2]),silent(1),silent(2),sounding(3,[0,4,7])],C,SCALE)
 assert d[1].selected.roman==d[0].selected.roman
 assert d[2].selected.roman==d[1].selected.roman
