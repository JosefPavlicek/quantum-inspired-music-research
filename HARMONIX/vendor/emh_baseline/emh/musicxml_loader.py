"""MusicXML loader for Explainable Melody Harmonizer.

Harmony annotations are deliberately ignored by the EMH input pipeline.
They may remain in MusicXML for human/reference readability.
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from music21 import converter, note, stream, chord, harmony

from emh.model import NoteEvent


@dataclass(frozen=True)
class MelodyData:
    notes: list[NoteEvent]
    time_signatures: dict[int, str]
    key_signature_fifths: int | None
    measure_count: int


def _fraction(value) -> Fraction:
    return Fraction(str(value)).limit_denominator(4096)


def _find_melody_part(score: stream.Score) -> stream.Part:
    parts = list(score.parts)
    if not parts:
        raise ValueError("MusicXML contains no musical part.")
    return parts[0]


def _validate_monophonic(part: stream.Part) -> None:
    """Reject actual simultaneous pitched chords, but ignore harmony labels.

    music21 ChordSymbol objects are also chord-like objects, so a plain
    isinstance(element, chord.Chord) incorrectly rejects <harmony> tags.
    """
    for element in part.recurse():
        if isinstance(element, harmony.Harmony):
            continue
        if isinstance(element, chord.Chord):
            raise ValueError(
                "Input must contain a monophonic melody; "
                "a simultaneous pitched chord event was found."
            )


def _extract_time_signatures(part: stream.Part) -> dict[int, str]:
    signatures = {}
    current_signature = None
    for measure_obj in part.getElementsByClass(stream.Measure):
        ts = measure_obj.getTimeSignatures()
        if ts:
            current_signature = ts[0].ratioString
        if current_signature is None:
            raise ValueError(
                f"No time signature is defined before measure {measure_obj.number}."
            )
        signatures[int(measure_obj.number)] = current_signature
    return signatures


def _extract_key_signature_fifths(part: stream.Part) -> int | None:
    from music21 import key
    for element in part.recurse():
        if isinstance(element, key.KeySignature):
            return int(element.sharps)
    return None


def load_musicxml(path: str | Path) -> MelodyData:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"MusicXML file not found: {path}")

    score = converter.parse(str(path))
    part = _find_melody_part(score)
    _validate_monophonic(part)

    time_signatures = _extract_time_signatures(part)
    key_signature_fifths = _extract_key_signature_fifths(part)

    events = []
    measures = list(part.getElementsByClass(stream.Measure))

    for measure_obj in measures:
        measure_number = int(measure_obj.number)
        for element in measure_obj.notesAndRests:
            if not isinstance(element, (note.Note, note.Rest)):
                continue

            duration = _fraction(element.duration.quarterLength)
            beat = _fraction(element.beat)
            onset = _fraction(element.getOffsetInHierarchy(part))
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
