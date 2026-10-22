from fractions import Fraction
from emh.model import NoteEvent,HarmonicSegment
from emh.harmony import generate_candidates
from emh.scoring import melody_compatibility,functional_transition,persistence,cadential_score,local_score

def seg(pcs):
 notes=[NoteEvent(str(pc),pc,Fraction(i),Fraction(1),1,Fraction(i+1),1.0,False) for i,pc in enumerate(pcs)]
 return HarmonicSegment(0,1,Fraction(1),Fraction(len(pcs)),notes)

def test_chord_tones_score_one():
 c={x.roman:x for x in generate_candidates("C")}
 assert melody_compatibility(seg([0,4,7]),c["I"],set(range(12)))==1.0

def test_diatonic_nonchord_tone_is_partial():
 c={x.roman:x for x in generate_candidates("C")}
 scale={0,2,4,5,7,9,11}
 assert melody_compatibility(seg([2]),c["I"],scale)==0.45

def test_functional_progression_pd_to_dominant_is_strong():
 c={x.roman:x for x in generate_candidates("C")}
 assert functional_transition(c["ii"],c["V"])==1.0
 assert functional_transition(c["V"],c["ii"])<1.0

def test_persistence_rewards_same_chord():
 c={x.roman:x for x in generate_candidates("C")}
 assert persistence(c["I"],c["I"])>persistence(c["I"],c["V"])

def test_final_authentic_cadence():
 c={x.roman:x for x in generate_candidates("C")}
 assert cadential_score(c["V"],c["I"],True)==1.0
 assert cadential_score(c["V"],c["vi"],True)==0.0

def test_weighted_local_score_is_reproducible():
 assert abs(local_score(1.0,1.0,0.55,1.0)-0.955)<1e-9
