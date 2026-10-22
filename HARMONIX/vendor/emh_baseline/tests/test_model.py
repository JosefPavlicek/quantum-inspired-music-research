from fractions import Fraction

from emh.model import NoteEvent


def test_note_event_exact_duration():
    note = NoteEvent(
        pitch="C4",
        pitch_class=0,
        onset=Fraction(0),
        duration=Fraction(3, 8),
        measure=1,
        beat=Fraction(1),
        metric_strength=1.5,
    )
    assert note.duration == Fraction(3, 8)
