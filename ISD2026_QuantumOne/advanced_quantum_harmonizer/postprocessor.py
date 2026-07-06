# postprocessor.py

from typing import Dict, List

from .beat_representation import BeatEvent
from .chord_library import ChordDef, midi_to_pc
from .config import OptimizerConfig
from .scoring import score_chord_sequence


def smooth_single_beat_spikes(
    chords: List[str],
    events: List[BeatEvent],
    chord_pool: Dict[str, ChordDef],
    cfg: OptimizerConfig,
) -> List[str]:
    """
    Removes local 1-beat harmonic spikes:
    A - B - A  =>  A - A - A
    if the replacement does not worsen score too much.
    """
    if len(chords) < 3:
        return chords[:]

    out = chords[:]

    for i in range(1, len(chords) - 1):
        left = out[i - 1]
        cur = out[i]
        right = out[i + 1]

        if left == right and cur != left:
            original_seq = out[max(0, i - 1):min(len(out), i + 2)]
            original_events = events[max(0, i - 1):min(len(events), i + 2)]

            trial = original_seq[:]
            trial[1] = left

            original_score = score_chord_sequence(original_events, original_seq, chord_pool, cfg)
            trial_score = score_chord_sequence(original_events, trial, chord_pool, cfg)

            if trial_score >= original_score - 0.25:
                out[i] = left

    return out


def stabilize_repeated_melody_notes(
    chords: List[str],
    events: List[BeatEvent],
    chord_pool: Dict[str, ChordDef],
    cfg: OptimizerConfig,
) -> List[str]:
    """
    If melody note repeats over adjacent beats, prefer not to change harmony too wildly
    unless the current harmony really helps.
    """
    if len(chords) < 2:
        return chords[:]

    out = chords[:]

    for i in range(1, len(chords)):
        prev_event = events[i - 1]
        cur_event = events[i]

        if prev_event.is_rest or cur_event.is_rest:
            continue

        prev_pcs = sorted(midi_to_pc(n) for n in prev_event.notes_midi)
        cur_pcs = sorted(midi_to_pc(n) for n in cur_event.notes_midi)

        if prev_pcs == cur_pcs and out[i] != out[i - 1]:
            original_seq = [out[i - 1], out[i]]
            original_events = [prev_event, cur_event]

            trial_seq = [out[i - 1], out[i - 1]]

            original_score = score_chord_sequence(original_events, original_seq, chord_pool, cfg)
            trial_score = score_chord_sequence(original_events, trial_seq, chord_pool, cfg)

            if trial_score >= original_score - 0.20:
                out[i] = out[i - 1]

    return out


def enforce_final_tonic(
    chords: List[str],
    chord_pool: Dict[str, ChordDef],
) -> List[str]:
    """
    Prefer tonic ending if available in the pool.
    """
    if not chords:
        return chords[:]

    out = chords[:]

    tonic_candidates = []
    if "Cmaj7" in chord_pool:
        tonic_candidates.append("Cmaj7")
    if "C" in chord_pool:
        tonic_candidates.append("C")

    if tonic_candidates:
        out[-1] = tonic_candidates[0]

    return out


def postprocess_harmony(
    chords: List[str],
    events: List[BeatEvent],
    chord_pool: Dict[str, ChordDef],
    cfg: OptimizerConfig,
) -> List[str]:
    out = chords[:]

    out = smooth_single_beat_spikes(out, events, chord_pool, cfg)
    out = stabilize_repeated_melody_notes(out, events, chord_pool, cfg)
    out = enforce_final_tonic(out, chord_pool)

    return out