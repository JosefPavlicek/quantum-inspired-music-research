from fractions import Fraction
from pathlib import Path

from emh.musicxml_loader import load_musicxml


FIXTURES = Path(__file__).parent / "fixtures"


def test_load_simple_4_4():
    melody = load_musicxml(
        FIXTURES / "test_4_4.musicxml"
    )

    assert melody.measure_count == 1
    assert melody.time_signatures[1] == "4/4"
    assert melody.key_signature_fifths == 0

    assert len(melody.notes) == 4

    pitches = [n.pitch for n in melody.notes]

    assert pitches == [
        "C4",
        "D4",
        "E4",
        "F4",
    ]


def test_preserves_exact_rhythm():
    melody = load_musicxml(
        FIXTURES / "test_4_4.musicxml"
    )

    durations = [
        n.duration for n in melody.notes
    ]

    assert durations == [
        Fraction(1),
        Fraction(1, 2),
        Fraction(1, 2),
        Fraction(2),
    ]


def test_preserves_onsets():
    melody = load_musicxml(
        FIXTURES / "test_4_4.musicxml"
    )

    onsets = [
        n.onset for n in melody.notes
    ]

    assert onsets == [
        Fraction(0),
        Fraction(1),
        Fraction(3, 2),
        Fraction(2),
    ]


def test_pitch_classes():
    melody = load_musicxml(
        FIXTURES / "test_4_4.musicxml"
    )

    pitch_classes = [
        n.pitch_class for n in melody.notes
    ]

    assert pitch_classes == [
        0,  # C
        2,  # D
        4,  # E
        5,  # F
    ]