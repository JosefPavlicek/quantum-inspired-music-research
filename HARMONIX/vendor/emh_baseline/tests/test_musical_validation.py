from fractions import Fraction
from emh.model import NoteEvent,HarmonicSegment
from emh.harmony import generate_candidates
from emh.optimizer import optimize

SCALE={0,2,4,5,7,9,11}
CANDS=generate_candidates("C")

def s(i, pcs):
    notes=[NoteEvent(str(pc),pc,Fraction(j),Fraction(1),i+1,Fraction(j+1),1.0,False) for j,pc in enumerate(pcs)]
    return HarmonicSegment(i,i+1,Fraction(1),Fraction(len(pcs)),notes)

def romans(segments):
    return [d.selected.roman for d in optimize(segments,CANDS,SCALE)]

def test_clear_tonic_dominant_tonic():
    path=romans([s(0,[0,4,7]),s(1,[7,11,2]),s(2,[0,4,7])])
    assert path[-1]=="I"
    assert path[1] in {"V","V7","vii°","viiø7"}

def test_predominant_dominant_tonic_shape():
    path=romans([s(0,[0,4,7]),s(1,[5,9,0]),s(2,[7,11,2]),s(3,[0,4,7])])
    assert path[-1]=="I"
    assert path[2] in {"V","V7","vii°","viiø7"}

def test_repeated_tonic_material_does_not_force_changes():
    path=romans([s(0,[0,4,7]),s(1,[0,4,7]),s(2,[0,4,7])])
    assert path.count("I") >= 2

def test_equal_dominant_fit_uses_explicit_tie_break():
    # G-B-D belongs equally to V and V7 in pitch-class membership;
    # the explicit tie rule must prefer the simpler V, not candidate list order.
    path=romans([s(0,[2,7,11])])
    # final cadence can favor I, so inspect a two-segment context ending on tonic
    path=romans([s(0,[2,7,11]),s(1,[0,4,7])])
    assert path[0]=="V"

def test_validation_suite_is_deterministic():
    material=[s(0,[0,4,7]),s(1,[5,9,0]),s(2,[7,11,2]),s(3,[0,4,7])]
    assert romans(material)==romans(material)
