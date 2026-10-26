import pytest
from harmonix.knowledge_candidates import generate,tonic_pc

def has(chords,pcs):return any(c.pitch_classes==frozenset(pcs) for c in chords)

def test_tonic_spelling():
    assert tonic_pc("Bb")==10
    assert tonic_pc("B-")==10
    assert tonic_pc("F#")==6
    with pytest.raises(ValueError):tonic_pc("H")

def test_c_major_corrected():
    c=generate("C","major","corrected")
    assert len(c)==10
    assert has(c,{7,11,2,5}) # G7, not Gmaj7
    assert not has(c,{7,11,2,6})
    assert has(c,{11,2,5,9}) # B half-diminished

def test_a_minor_corrected():
    c=generate("A","minor","corrected")
    assert len(c)==10
    assert has(c,{4,8,11}) # E major
    assert has(c,{4,8,11,2}) # E7
    assert has(c,{11,2,5,9}) # B half-diminished

def test_extended():
    c=generate("C","major","extended")
    assert len(c)==19
    assert has(c,{0,4,7,11}) # Cmaj7
    assert has(c,{9,1,4,7}) # A7, V7/ii
    assert len(generate("A","minor","extended"))==19

def test_reject_baseline_approximation():
    with pytest.raises(ValueError):generate("C","major","baseline")
