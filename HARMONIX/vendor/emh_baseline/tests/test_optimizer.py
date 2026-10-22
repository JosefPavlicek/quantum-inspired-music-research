from fractions import Fraction
from emh.model import NoteEvent,HarmonicSegment
from emh.harmony import generate_candidates
from emh.optimizer import optimize

SCALE={0,2,4,5,7,9,11}
def segment(i,pcs):
 notes=[NoteEvent(str(pc),pc,Fraction(j),Fraction(1),i+1,Fraction(j+1),1.0,False) for j,pc in enumerate(pcs)]
 return HarmonicSegment(i,i+1,Fraction(1),Fraction(len(pcs)),notes)

def test_optimizer_returns_one_decision_per_segment():
 d=optimize([segment(0,[0,4,7]),segment(1,[7,11,2]),segment(2,[0,4,7])],generate_candidates("C"),SCALE)
 assert len(d)==3

def test_optimizer_finishes_on_tonic_for_clear_cadence():
 d=optimize([segment(0,[5,9]),segment(1,[7,11,2]),segment(2,[0,4,7])],generate_candidates("C"),SCALE)
 assert d[-1].selected.roman=="I"

def test_path_score_is_accumulated():
 d=optimize([segment(0,[0,4,7]),segment(1,[7,11,2]),segment(2,[0,4,7])],generate_candidates("C"),SCALE)
 assert d[-1].scores.path_score >= d[-1].scores.local_score

def test_explanations_keep_components_and_alternatives():
 d=optimize([segment(0,[0,4,7]),segment(1,[7,11,2])],generate_candidates("C"),SCALE)
 assert 0 <= d[0].scores.melody_compatibility <= 1
 assert len(d[0].alternatives)==3

def test_optimizer_is_deterministic():
 s=[segment(0,[0,4,7]),segment(1,[2,5,9]),segment(2,[7,11,2]),segment(3,[0,4,7])]
 c=generate_candidates("C")
 a=[x.selected.roman for x in optimize(s,c,SCALE)]
 b=[x.selected.roman for x in optimize(s,c,SCALE)]
 assert a==b
