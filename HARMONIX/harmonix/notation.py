"""Display-only pitch names and Nashville degree labels; not internal identifiers.

NNS varies by community. This module emits a simple explicit numeric degree,
with accidentals relative to the supplied MAJOR key; it is not Roman analysis.
"""
from __future__ import annotations
from .knowledge import Chord, Quality

CZECH_SHARP = ('C', 'Cis', 'D', 'Dis', 'E', 'F', 'Fis', 'G', 'Gis', 'A', 'Ais', 'H')
EN_SHARP = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
MAJOR_DEGREES = (0, 2, 4, 5, 7, 9, 11)
QUALITIES = {
    Quality.MAJOR: '', Quality.MINOR: 'm', Quality.DIMINISHED: 'dim',
    Quality.AUGMENTED: 'aug', Quality.SUS2: 'sus2', Quality.SUS4: 'sus4',
}


def pitch_name(pc: int, *, czech: bool = True) -> str:
    if not 0 <= pc <= 11:
        raise ValueError('pitch class out of range')
    return (CZECH_SHARP if czech else EN_SHARP)[pc]


def chord_label(chord: Chord, *, czech: bool = True) -> str:
    """Simple labels for triads, slash bass and common sevenths.

    Raises for more complex structures rather than emitting misleading notation.
    """
    base = chord.quality
    ext = chord.extensions
    if chord.omit_intervals or chord.add_intervals:
        raise NotImplementedError('Complex altered/omitted chord labels not implemented')
    if ext == ():
        suffix = QUALITIES[base]
    elif ext == (10,) and base == Quality.MAJOR:
        suffix = '7'
    elif ext == (11,) and base == Quality.MAJOR:
        suffix = 'maj7'
    elif ext == (10,) and base == Quality.MINOR:
        suffix = 'm7'
    else:
        raise NotImplementedError('Chord label for this extension combination not implemented')
    label = pitch_name(chord.root_pc, czech=czech) + suffix
    if chord.effective_bass_pc != chord.root_pc:
        label += '/' + pitch_name(chord.effective_bass_pc, czech=czech)
    return label


def _degree(pc: int, tonic_pc: int) -> str:
    diff = (pc - tonic_pc) % 12
    for idx, semitones in enumerate(MAJOR_DEGREES, start=1):
        if diff == semitones:
            return str(idx)
    for idx, semitones in enumerate(MAJOR_DEGREES, start=1):
        if diff == (semitones + 1) % 12:
            return '#' + str(idx)
    raise AssertionError('Unreachable chromatic degree')


def nashville_label(chord: Chord, tonic_pc: int) -> str:
    """NNS-style numeric label; slash-bass is a SCALE DEGREE, not inversion index.

    Major-key reference only. Secondary function is not inferred from this label.
    """
    if not 0 <= tonic_pc <= 11:
        raise ValueError('tonic_pc must be in 0..11')
    suffix = QUALITIES[chord.quality]
    if chord.extensions == (10,) and chord.quality == Quality.MAJOR:
        suffix = '7'
    elif chord.extensions == (10,) and chord.quality == Quality.MINOR:
        suffix = 'm7'
    elif chord.extensions == (11,) and chord.quality == Quality.MAJOR:
        suffix = 'maj7'
    elif chord.extensions or chord.add_intervals or chord.omit_intervals:
        raise NotImplementedError('Complex Nashville extensions not implemented')
    label = _degree(chord.root_pc, tonic_pc) + suffix
    if chord.effective_bass_pc != chord.root_pc:
        label += '/' + _degree(chord.effective_bass_pc, tonic_pc)
    return label
