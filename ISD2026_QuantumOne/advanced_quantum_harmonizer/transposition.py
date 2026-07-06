
# transposition.py

from __future__ import annotations

import xml.etree.ElementTree as ET

from .chord_library import PC_TO_SEMITONE


MAJOR_KEY_BY_FIFTHS = {
    -7: "Cb",
    -6: "Gb",
    -5: "Db",
    -4: "Ab",
    -3: "Eb",
    -2: "Bb",
    -1: "F",
     0: "C",
     1: "G",
     2: "D",
     3: "A",
     4: "E",
     5: "B",
     6: "Gb",  # enharmonic F#
     7: "Db",  # enharmonic C#
}

MINOR_KEY_BY_FIFTHS = {
    -7: "Ab",
    -6: "Eb",
    -5: "Bb",
    -4: "F",
    -3: "C",
    -2: "G",
    -1: "D",
     0: "A",
     1: "E",
     2: "B",
     3: "Gb",  # enharmonic F# minor
     4: "Db",  # enharmonic C# minor
     5: "Ab",  # enharmonic G# minor
     6: "Eb",  # enharmonic D# minor
     7: "Bb",  # enharmonic A# minor
}


def detect_key_simple(pitch_classes: list[str]) -> str:
    """
    Legacy placeholder kept for compatibility.
    Prefer detect_key_from_musicxml(xml_path).
    """
    return "C"


def detect_key_from_musicxml(xml_path: str) -> str:
    """
    Detect tonic directly from MusicXML <key><fifths> and optional <mode>.
    This is automatic and works per score, so nothing needs to be manually
    configured for each song.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    first_fifths = root.find('.//part/measure/attributes/key/fifths')
    if first_fifths is None or first_fifths.text is None:
        return "C"

    try:
        fifths = int(first_fifths.text.strip())
    except ValueError:
        return "C"

    mode_tag = root.find('.//part/measure/attributes/key/mode')
    mode = (mode_tag.text.strip().lower() if mode_tag is not None and mode_tag.text else 'major')

    if mode == 'minor':
        return MINOR_KEY_BY_FIFTHS.get(fifths, 'A')
    return MAJOR_KEY_BY_FIFTHS.get(fifths, 'C')


def compute_transposition_interval(from_key: str, to_key: str = "C") -> int:
    """
    Returns semitone shift needed to transpose from 'from_key' to 'to_key'.
    """
    if from_key not in PC_TO_SEMITONE:
        raise ValueError(f"Unknown source key: {from_key}")
    if to_key not in PC_TO_SEMITONE:
        raise ValueError(f"Unknown target key: {to_key}")
    return PC_TO_SEMITONE[to_key] - PC_TO_SEMITONE[from_key]


def transpose_midi(midi_note: int, semitone_shift: int) -> int:
    return midi_note + semitone_shift


def transpose_notes(notes: list[int], semitone_shift: int) -> list[int]:
    return [n + semitone_shift for n in notes]


def transpose_events(events, semitone_shift: int):
    for ev in events:
        ev.notes_midi = transpose_notes(ev.notes_midi, semitone_shift)
    return events


def transpose_events_to_c(events, detected_key: str):
    """
    Applies transposition to all BeatEvents according to the detected key.
    Returns the same event list mutated in place.
    """
    shift = compute_transposition_interval(detected_key, "C")
    return transpose_events(events, shift)