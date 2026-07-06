# candidate_selector.py

from typing import List, Dict, Optional

from .beat_representation import BeatEvent
from .chord_library import (
    ChordDef,
    build_chord_pool,
    midi_to_pc,
    chords_containing_pitch_classes,
    chords_matching_any_pitch_class,
    DOM_TARGETS,
)


def extract_pitch_classes(event: BeatEvent) -> List[str]:
    return [midi_to_pc(m) for m in event.notes_midi]


def rank_candidates_for_event(
    event: BeatEvent,
    chord_pool: Dict[str, ChordDef],
    prev_chord_name: Optional[str] = None,
    next_expected_function: Optional[str] = None,
) -> List[str]:
    """
    Returns candidate chord names sorted by a simple heuristic ranking.
    """
    pcs = extract_pitch_classes(event)

    full_match = chords_containing_pitch_classes(chord_pool, pcs) if pcs else []
    partial_match = chords_matching_any_pitch_class(chord_pool, pcs) if pcs else list(chord_pool.keys())

    scored = []

    for name, chord in chord_pool.items():
        score = 0.0

        # full / partial melody coverage
        if name in full_match:
            score += 5.0
        elif name in partial_match:
            score += 2.0

        # strong beat preference: stable functions
        if event.is_strong:
            if chord.function == "T":
                score += 1.5
            elif chord.function == "D":
                score += 1.0

        # weak beat allows more motion
        if not event.is_strong and chord.function == "S":
            score += 0.5

        # if previous chord known, prefer smooth functional continuation
        if prev_chord_name is not None:
            prev_func = chord_pool[prev_chord_name].function if prev_chord_name in chord_pool else None
            if prev_func == "T" and chord.function == "S":
                score += 1.2
            elif prev_func == "S" and chord.function == "D":
                score += 1.2
            elif prev_func == "D" and chord.function == "T":
                score += 1.5
            elif prev_func == chord.function:
                score += 0.4

        # if we know what should come next, help prepare it
        if next_expected_function is not None:
            if chord.function == next_expected_function:
                score += 0.8

        # slight preference for diatonic harmony
        if name not in DOM_TARGETS:
            score += 0.3

        # prefer seventh chords on strong beats if enabled in pool
        if event.is_strong and chord.chord_type == "seventh":
            score += 0.4

        scored.append((score, name))

    scored.sort(reverse=True, key=lambda x: (x[0], x[1]))
    return [name for _, name in scored]


def pick_top_k_candidates(
    event: BeatEvent,
    chord_pool: Dict[str, ChordDef],
    prev_chord_name: Optional[str] = None,
    next_expected_function: Optional[str] = None,
    k: int = 8,
) -> List[str]:
    ranked = rank_candidates_for_event(
        event=event,
        chord_pool=chord_pool,
        prev_chord_name=prev_chord_name,
        next_expected_function=next_expected_function,
    )

    out = ranked[:k]

    # pad if necessary
    if len(out) < k:
        names = list(chord_pool.keys())
        i = 0
        while len(out) < k and i < len(names):
            if names[i] not in out:
                out.append(names[i])
            i += 1

    return out

