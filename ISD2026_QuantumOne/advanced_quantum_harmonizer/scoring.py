# scoring.py

from typing import Dict, List, Optional

from .beat_representation import BeatEvent
from .chord_library import ChordDef, midi_to_pc, DOM_TARGETS
from .config import OptimizerConfig


def melody_fit_score(event: BeatEvent, chord: ChordDef, cfg: OptimizerConfig) -> float:
    if event.is_rest:
        return 0.0

    pcs = [midi_to_pc(n) for n in event.notes_midi]
    chord_tones = chord.tone_set

    covered = sum(1 for pc in pcs if pc in chord_tones)
    ratio = covered / max(1, len(pcs))

    return cfg.w_melody_fit * ratio


def register_fit_score(event: BeatEvent, chord: ChordDef, cfg: OptimizerConfig) -> float:
    if event.is_rest:
        return 0.0

    score = 0.0

    low = event.lowest_note
    high = event.highest_note

    if low is not None:
        low_pc = midi_to_pc(low)
        if low_pc == chord.root:
            score += 1.0
        elif low_pc in chord.tone_set:
            score += 0.5

    if high is not None:
        high_pc = midi_to_pc(high)
        if chord.third is not None and high_pc == chord.third:
            score += 0.8
        elif chord.seventh is not None and high_pc == chord.seventh:
            score += 0.8
        elif high_pc in chord.tone_set:
            score += 0.4

    return cfg.w_register_fit * score


def metric_position_score(event: BeatEvent, chord: ChordDef, cfg: OptimizerConfig) -> float:
    score = event.metric_weight

    if event.is_strong:
        if chord.function == "T":
            score += 0.7
        elif chord.function == "D":
            score += 0.4
    else:
        if chord.function == "S":
            score += 0.3

    return cfg.w_metric_fit * score


def strong_beat_penalty(event: BeatEvent, chord: ChordDef, cfg: OptimizerConfig) -> float:
    if not event.is_strong or event.is_rest:
        return 0.0

    pcs = [midi_to_pc(n) for n in event.notes_midi]
    if any(pc not in chord.tone_set for pc in pcs):
        return -cfg.w_strong_beat_penalty

    return 0.0


def local_chord_score(
    event: BeatEvent,
    chord: ChordDef,
    cfg: OptimizerConfig,
    is_first_beat_of_piece: bool = False,
    is_last_beat_of_piece: bool = False,
) -> float:
    score = 0.0
    score += melody_fit_score(event, chord, cfg)
    score += register_fit_score(event, chord, cfg)
    score += metric_position_score(event, chord, cfg)
    score += strong_beat_penalty(event, chord, cfg)

    if is_first_beat_of_piece and chord.root == "C":
        score += cfg.w_initial_tonic_bonus

    if is_last_beat_of_piece and chord.root == "C":
        score += cfg.w_final_tonic_bonus

    return score


def functional_flow_score(
    prev_chord: Optional[ChordDef],
    cur_chord: ChordDef,
    cfg: OptimizerConfig,
) -> float:
    if prev_chord is None:
        return 0.0

    a = prev_chord.function
    b = cur_chord.function

    if (a, b) == ("T", "S"):
        return cfg.w_functional_flow * 1.0
    if (a, b) == ("S", "D"):
        return cfg.w_functional_flow * 1.0
    if (a, b) == ("D", "T"):
        return cfg.w_functional_flow * 1.3
    if a == b:
        return cfg.w_functional_flow * 0.35

    return -cfg.w_functional_flow * 0.25


def common_tone_score(prev_chord: Optional[ChordDef], cur_chord: ChordDef, cfg: OptimizerConfig) -> float:
    if prev_chord is None:
        return 0.0

    common = len(prev_chord.tone_set.intersection(cur_chord.tone_set))
    return cfg.w_common_tone * common


def secondary_resolution_score(
    cur_chord_name: str,
    next_chord_name: Optional[str],
    cfg: OptimizerConfig,
) -> float:
    if cur_chord_name in DOM_TARGETS:
        target = DOM_TARGETS[cur_chord_name]
        if next_chord_name == target or (next_chord_name is not None and next_chord_name.startswith(target)):
            return 1.2
        return -0.4
    return 0.0


def score_chord_sequence(
    events: List[BeatEvent],
    chord_names: List[str],
    chord_pool: Dict[str, ChordDef],
    cfg: OptimizerConfig,
) -> float:
    if len(events) != len(chord_names):
        raise ValueError("events and chord_names must have the same length")

    total = 0.0
    prev = None

    for i, (event, chord_name) in enumerate(zip(events, chord_names)):
        chord = chord_pool[chord_name]

        total += local_chord_score(
            event=event,
            chord=chord,
            cfg=cfg,
            is_first_beat_of_piece=(i == 0),
            is_last_beat_of_piece=(i == len(events) - 1),
        )
        total += functional_flow_score(prev, chord, cfg)
        total += common_tone_score(prev, chord, cfg)

        if i < len(chord_names) - 1:
            total += secondary_resolution_score(chord_name, chord_names[i + 1], cfg)

        prev = chord

    return total