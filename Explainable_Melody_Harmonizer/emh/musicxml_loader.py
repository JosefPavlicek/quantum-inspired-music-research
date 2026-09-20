"""MusicXML loader for Explainable Melody Harmonizer.

music21 is used only as the MusicXML parsing layer. The harmonization
algorithm works with EMH's own internal data structures.

Important principles:
- preserve the original time signature,
- preserve rhythmic durations,
- preserve rests,
- do not quantize the melody to beats,
- do not read or use original harmony annotations.
"""

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from music21 import converter, meter, note, stream

from emh.model import NoteEvent


@dataclass(frozen=True)
class MelodyData:
    """Parsed monophonic melody and its basic musical metadata."""

    notes: list[NoteEvent]
    time_signatures: dict[int, str]
    key_signature_fifths: int | None
    measure_count: int


def _fraction(value) -> Fraction:
    """Convert music21 numeric values safely to Fraction."""

    return Fraction(str(value)).limit_denominator(4096)


def _find_melody_part(score: stream.Score) -> stream.Part:
    """Return the first musical part.

    EMH v1 expects a monophonic melody input. Multi-part score selection
    can be made configurable later.
    """

    parts = list(score.parts)

    if not parts:
        raise ValueError("MusicXML contains no musical part.")

    return parts[0]


def _validate_monophonic(part: stream.Part) -> None:
    """Reject explicit chord events.

    Polyphonic voices will be handled separately later if required.
    EMH v1 deliberately expects a clean monophonic melody.
    """

    from music21 import chord

    for element in part.recurse():
        if isinstance(element, chord.Chord):
            raise ValueError(
                "Input must contain a monophonic melody; "
                "a chord event was found."
            )


def _extract_time_signatures(part: stream.Part) -> dict[int, str]:
    """Return time-signature changes indexed by measure number."""

    signatures: dict[int, str] = {}
    current_signature: str | None = None

    for measure_obj in part.getElementsByClass(stream.Measure):
        ts = measure_obj.getTimeSignatures()

        if ts:
            current_signature = ts[0].ratioString

        if current_signature is None:
            raise ValueError(
                f"No time signature is defined before measure "
                f"{measure_obj.number}."
            )

        signatures[int(measure_obj.number)] = current_signature

    return signatures


def _extract_key_signature_fifths(part: stream.Part) -> int | None:
    """Read the first explicit MusicXML key signature.

    We intentionally do not infer the key here. Key estimation, when
    required, belongs to a separate later stage.
    """

    from music21 import key

    for element in part.recurse():
        if isinstance(element, key.KeySignature):
            return int(element.sharps)

    return None


def load_musicxml(path: str | Path) -> MelodyData:
    """Load a monophonic MusicXML melody into EMH's internal model."""

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"MusicXML file not found: {path}")

    score = converter.parse(str(path))
    part = _find_melody_part(score)

    _validate_monophonic(part)

    time_signatures = _extract_time_signatures(part)
    key_signature_fifths = _extract_key_signature_fifths(part)

    events: list[NoteEvent] = []

    measures = list(part.getElementsByClass(stream.Measure))

    for measure_obj in measures:
        measure_number = int(measure_obj.number)

        for element in measure_obj.notesAndRests:

            if not isinstance(element, (note.Note, note.Rest)):
                continue

            duration = _fraction(element.duration.quarterLength)

            # Beat is expressed in quarter-length beat units by music21.
            beat = _fraction(element.beat)

            # Global onset from the beginning of the part.
            onset = _fraction(
                element.getOffsetInHierarchy(part)
            )

            is_rest = isinstance(element, note.Rest)

            if is_rest:
                pitch_name = None
                pitch_class = None
            else:
                pitch_name = element.pitch.nameWithOctave
                pitch_class = int(element.pitch.pitchClass)

            events.append(
                NoteEvent(
                    pitch=pitch_name,
                    pitch_class=pitch_class,
                    onset=onset,
                    duration=duration,
                    measure=measure_number,
                    beat=beat,
                    metric_strength=float(element.beatStrength),
                    is_rest=is_rest,
                )
            )

    if not events:
        raise ValueError("MusicXML contains no notes or rests.")

    return MelodyData(
        notes=events,
        time_signatures=time_signatures,
        key_signature_fifths=key_signature_fifths,
        measure_count=len(measures),
    )