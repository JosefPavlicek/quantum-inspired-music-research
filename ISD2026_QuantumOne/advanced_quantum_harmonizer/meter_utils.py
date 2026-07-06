# meter_utils.py

from typing import List
from .config import SUPPORTED_METERS, MeterProfile


def get_meter_profile(meter_str: str) -> MeterProfile:
    if meter_str not in SUPPORTED_METERS:
        raise ValueError(f"Unsupported meter: {meter_str}")
    return SUPPORTED_METERS[meter_str]


def compute_metric_weight(meter: str, beat_in_bar: int) -> float:
    profile = get_meter_profile(meter)
    return profile.metric_weight(beat_in_bar)


def is_strong_beat(meter: str, beat_in_bar: int) -> bool:
    profile = get_meter_profile(meter)
    return beat_in_bar in profile.strong_beats


def expand_durations_to_beats(
    note_events: List[tuple],  # (midi_notes, duration_in_beats)
    beats_per_bar: int
):
    """
    Converts duration-based notes into per-beat representation.

    Example:
    [([60],2), ([62],2)] → [[60],[60],[62],[62]]
    """
    beats = []

    for notes, dur in note_events:
        reps = int(round(dur))
        for _ in range(reps):
            beats.append(notes)

    # pad or trim
    if len(beats) < beats_per_bar:
        beats.extend([[]] * (beats_per_bar - len(beats)))
    elif len(beats) > beats_per_bar:
        beats = beats[:beats_per_bar]

    return beats