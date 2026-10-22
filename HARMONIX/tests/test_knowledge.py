import pytest
from harmonix.knowledge import Chord, Quality, Voicing, classify_change
from harmonix.notation import chord_label, nashville_label


def test_triads_and_inversions():
    c = Chord(0, Quality.MAJOR)
    c_e = Chord(0, Quality.MAJOR, bass_pc=4)
    c_g = Chord(0, Quality.MAJOR, bass_pc=7)
    assert (c.inversion, c_e.inversion, c_g.inversion) == (0, 1, 2)
    assert c.harmonic_identity() == c_e.harmonic_identity() == c_g.harmonic_identity()
    assert len({c.realization_identity(), c_e.realization_identity(), c_g.realization_identity()}) == 3
    assert classify_change(c, c_e) == 'bass_or_inversion_change'
    assert chord_label(c_e) == 'C/E'
    assert nashville_label(c_e, 0) == '1/3'
    assert nashville_label(c_g, 0) == '1/5'


def test_seventh_inversion_czech_b():
    g7_h = Chord(7, Quality.MAJOR, extensions=(10,), bass_pc=11)
    assert g7_h.inversion == 1
    assert chord_label(g7_h) == 'G7/H'
    assert chord_label(g7_h, czech=False) == 'G7/B'
    assert nashville_label(g7_h, 0) == '5' + '7/7'


def test_added_sixth_not_first_inversion():
    c6 = Chord(0, Quality.MAJOR, add_intervals=(9,), bass_pc=9)
    assert c6.inversion is None
    assert c6.pitch_classes == {0, 4, 7, 9}
    assert c6.harmonic_identity() != Chord(0, Quality.MAJOR).harmonic_identity()


def test_voicing_separate_from_chord():
    c_e = Chord(0, Quality.MAJOR, bass_pc=4)
    assert Voicing((52, 60, 67)).matches(c_e)
    assert Voicing((48, 64, 67)).matches(c_e) is False


def test_invalid_pitch_classes():
    with pytest.raises(ValueError):
        Chord(12, Quality.MAJOR)
    with pytest.raises(ValueError):
        Chord(0, Quality.MAJOR, bass_pc=-1)


def test_function_annotation_not_identity():
    a = Chord(7, Quality.MAJOR, function='dominant')
    b = Chord(7, Quality.MAJOR, function='other')
    assert a.harmonic_identity() == b.harmonic_identity()


def test_unsupported_notation_is_explicit():
    c9 = Chord(0, Quality.MAJOR, extensions=(10, 14))
    with pytest.raises(NotImplementedError):
        chord_label(c9)
    with pytest.raises(NotImplementedError):
        nashville_label(c9, 0)
