# musicxml_loader.py

import xml.etree.ElementTree as ET
from typing import List, Tuple

from .beat_representation import BeatEvent
from .meter_utils import is_strong_beat, compute_metric_weight
from .config import SUPPORTED_METERS


PC_TO_SEMITONE = {
    "C": 0, "C#": 1, "Db": 1,
    "D": 2, "D#": 3, "Eb": 3,
    "E": 4,
    "F": 5, "F#": 6, "Gb": 6,
    "G": 7, "G#": 8, "Ab": 8,
    "A": 9, "A#": 10, "Bb": 10,
    "B": 11,
}


def step_to_pc(step: str, alter: int) -> str:
    if alter == 1:
        return step + "#"
    if alter == -1:
        return step + "b"
    return step


def pitch_to_midi(step: str, alter: int, octave: int) -> int:
    pc = step_to_pc(step, alter)
    semitone = PC_TO_SEMITONE[pc]
    return 12 * (octave + 1) + semitone


def parse_musicxml_measures(xml_path: str):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    part = root.find(".//part")
    if part is None:
        raise ValueError("No <part> found in MusicXML.")

    measures = part.findall("measure")
    if not measures:
        raise ValueError("No <measure> found in MusicXML.")

    parsed_measures = []

    current_meter = "4/4"
    current_divisions = 1

    for measure in measures:
        attributes = measure.find("attributes")
        if attributes is not None:
            divisions_tag = attributes.find("divisions")
            if divisions_tag is not None and divisions_tag.text:
                current_divisions = int(divisions_tag.text)

            time_tag = attributes.find("time")
            if time_tag is not None:
                beats_tag = time_tag.find("beats")
                beat_type_tag = time_tag.find("beat-type")
                if beats_tag is not None and beat_type_tag is not None:
                    current_meter = f"{beats_tag.text}/{beat_type_tag.text}"

        if current_meter not in SUPPORTED_METERS:
            raise ValueError(f"Unsupported meter in file: {current_meter}")

        beats_str, beat_type_str = current_meter.split("/")
        beats_per_bar = int(beats_str)
        beat_type = int(beat_type_str)

        # Internal representation of notes in this measure:
        # list of (notes_midi, duration_in_beats)
        measure_events: List[Tuple[List[int], float]] = []

        last_event_index = None

        for note in measure.findall("note"):
            duration_tag = note.find("duration")
            duration_divisions = int(duration_tag.text) if duration_tag is not None else 0

            # Convert MusicXML duration units into "beats of current meter"
            # quarter note in 4/4 = 1 beat
            # eighth note in 6/8 = 1 beat
            duration_beats = (duration_divisions / current_divisions) * (beat_type / 4.0)

            is_rest = note.find("rest") is not None
            is_chord_tone = note.find("chord") is not None

            if is_rest:
                measure_events.append(([], duration_beats))
                last_event_index = len(measure_events) - 1
                continue

            pitch = note.find("pitch")
            if pitch is None:
                continue

            step = pitch.find("step").text
            octave = int(pitch.find("octave").text)

            alter_tag = pitch.find("alter")
            alter = int(alter_tag.text) if alter_tag is not None else 0

            midi = pitch_to_midi(step, alter, octave)

            if is_chord_tone and last_event_index is not None:
                # Append pitch to previous event (simultaneous tone)
                prev_notes, prev_duration = measure_events[last_event_index]
                prev_notes = prev_notes + [midi]
                measure_events[last_event_index] = (prev_notes, prev_duration)
            else:
                measure_events.append(([midi], duration_beats))
                last_event_index = len(measure_events) - 1

        parsed_measures.append({
            "meter": current_meter,
            "beats_per_bar": beats_per_bar,
            "beat_type": beat_type,
            "divisions": current_divisions,
            "events": measure_events,
        })

    return parsed_measures


def quantize_measure_to_beats(
    measure_events: List[Tuple[List[int], float]],
    beats_per_bar: int,
    align_right: bool = False,
) -> List[List[int]]:
    """
    Expand measure events into one item per beat.
    Each beat contains:
    - [] for rest
    - [midi] for single note
    - [midi1, midi2, ...] for simultaneity

    This is a beat-quantized approximation, intended for harmonization.
    """
    beat_grid: List[List[int]] = []

    for notes, duration_beats in measure_events:
        reps = max(1, int(round(duration_beats)))
        for _ in range(reps):
            beat_grid.append(notes[:])

    if len(beat_grid) < beats_per_bar:
        missing = beats_per_bar - len(beat_grid)
        padding = [[] for _ in range(missing)]
        if align_right:
            beat_grid = padding + beat_grid
        else:
            beat_grid.extend(padding)
    elif len(beat_grid) > beats_per_bar:
        beat_grid = beat_grid[:beats_per_bar]

    return beat_grid


def musicxml_to_beats(xml_path: str) -> List[BeatEvent]:
    parsed_measures = parse_musicxml_measures(xml_path)

    beats_all: List[BeatEvent] = []
    global_idx = 0

    for bar_idx, measure in enumerate(parsed_measures):
        meter = measure["meter"]
        beats_per_bar = measure["beats_per_bar"]

        total_beats = sum(duration for _, duration in measure["events"])
        align_right = (bar_idx == 0 and total_beats < beats_per_bar)

        beat_notes = quantize_measure_to_beats(
            measure_events=measure["events"],
            beats_per_bar=beats_per_bar,
            align_right=align_right,
        )

        for beat_idx, notes in enumerate(beat_notes):
            ev = BeatEvent(
                global_beat_index=global_idx,
                bar_index=bar_idx,
                beat_in_bar=beat_idx,
                notes_midi=notes[:],
                duration_units=1.0,
                is_strong=is_strong_beat(meter, beat_idx),
                metric_weight=compute_metric_weight(meter, beat_idx),
                meter=meter,
            )
            beats_all.append(ev)
            global_idx += 1

    return beats_all