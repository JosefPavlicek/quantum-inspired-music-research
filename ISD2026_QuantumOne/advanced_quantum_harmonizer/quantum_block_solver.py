# quantum_block_solver.py

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import math
import random

from .beat_representation import BeatEvent
from .chord_library import ChordDef
from .candidate_selector import pick_top_k_candidates
from .scoring import (
    local_chord_score,
    functional_flow_score,
    common_tone_score,
    secondary_resolution_score,
    score_chord_sequence,
)
from .config import OptimizerConfig


@dataclass
class QuantumBlockResult:
    start_beat: int
    end_beat: int
    chords: List[str]
    local_scores: List[float] = field(default_factory=list)
    state_probability: float = 0.0
    gamma: float = 0.0
    beta: float = 0.0
    metadata: Dict = field(default_factory=dict)


# ============================================================
# Candidate preparation
# ============================================================

def build_candidate_matrix(
    block_events: List[BeatEvent],
    chord_pool: Dict[str, ChordDef],
    candidate_count: int = 8,
) -> List[List[str]]:
    matrix: List[List[str]] = []

    prev_best = None
    for i, event in enumerate(block_events):
        next_expected_function = None

        if i == len(block_events) - 1:
            next_expected_function = "T"
        elif event.is_strong:
            next_expected_function = "T"

        cands = pick_top_k_candidates(
            event=event,
            chord_pool=chord_pool,
            prev_chord_name=prev_best,
            next_expected_function=next_expected_function,
            k=candidate_count,
        )

        matrix.append(cands)

        if cands:
            prev_best = cands[0]

    return matrix


# ============================================================
# Classical beam-search baseline
# ============================================================

def solve_block_beam_search(
    block_events: List[BeatEvent],
    chord_pool: Dict[str, ChordDef],
    cfg: OptimizerConfig,
    block_index: int = 0,
    beam_width: int = 24,
    candidate_count: int = 8,
    is_first_block: bool = False,
    is_last_block: bool = False,
) -> QuantumBlockResult:
    if not block_events:
        raise ValueError("block_events cannot be empty")

    candidate_matrix = build_candidate_matrix(
        block_events=block_events,
        chord_pool=chord_pool,
        candidate_count=candidate_count,
    )

    beam: List[Tuple[List[str], List[float], float]] = [([], [], 0.0)]

    for i, event in enumerate(block_events):
        new_beam: List[Tuple[List[str], List[float], float]] = []

        is_first_beat_of_piece = is_first_block and (i == 0)
        is_last_beat_of_piece = is_last_block and (i == len(block_events) - 1)

        for seq, local_scores, total_score in beam:
            prev_name = seq[-1] if seq else None

            for cand_name in candidate_matrix[i]:
                chord = chord_pool[cand_name]

                local = local_chord_score(
                    event=event,
                    chord=chord,
                    cfg=cfg,
                    is_first_beat_of_piece=is_first_beat_of_piece,
                    is_last_beat_of_piece=is_last_beat_of_piece,
                )

                transition = 0.0
                if prev_name is not None:
                    transition += functional_flow_score(chord_pool[prev_name], chord, cfg)
                    transition += common_tone_score(chord_pool[prev_name], chord, cfg)

                new_seq = seq + [cand_name]
                new_local_scores = local_scores + [local]
                new_total = total_score + local + transition

                new_beam.append((new_seq, new_local_scores, new_total))

        new_beam.sort(key=lambda x: x[2], reverse=True)
        beam = new_beam[:beam_width]

    rescored = []
    for seq, local_scores, total_score in beam:
        final_score = total_score
        for i in range(len(seq) - 1):
            final_score += secondary_resolution_score(seq[i], seq[i + 1], cfg)
        rescored.append((seq, local_scores, final_score))

    rescored.sort(key=lambda x: x[2], reverse=True)
    best_seq, best_local_scores, best_score = rescored[0]

    return QuantumBlockResult(
        start_beat=block_events[0].global_beat_index,
        end_beat=block_events[-1].global_beat_index,
        chords=best_seq,
        local_scores=best_local_scores,
        state_probability=1.0,
        gamma=0.0,
        beta=0.0,
        metadata={
            "solver": "beam_search",
            "block_index": block_index,
            "beam_width": beam_width,
            "candidate_count": candidate_count,
            "block_score": best_score,
        },
    )


# ============================================================
# Quantum-inspired helpers
# ============================================================

def _softmax(values: List[float], temperature: float = 1.0) -> List[float]:
    if not values:
        return []

    if temperature <= 0:
        temperature = 1.0

    mx = max(values)
    exps = [math.exp((v - mx) / temperature) for v in values]
    s = sum(exps)
    if s <= 0:
        return [1.0 / len(values)] * len(values)
    return [e / s for e in exps]


def _normalize_weight_dict(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, v) for v in weights.values())
    if total <= 0:
        n = len(weights)
        if n == 0:
            return {}
        return {k: 1.0 / n for k in weights}
    return {k: max(0.0, v) / total for k, v in weights.items()}


def _sample_from_distribution(weight_dict: Dict[str, float], rng: random.Random) -> str:
    items = list(weight_dict.keys())
    probs = list(weight_dict.values())

    if not items:
        raise ValueError("Cannot sample from empty distribution.")

    total = sum(probs)
    if total <= 0:
        return rng.choice(items)

    r = rng.random()
    acc = 0.0
    for item, p in zip(items, probs):
        acc += p / total
        if r <= acc:
            return item
    return items[-1]


def _compute_local_scores_for_sequence(
    seq: List[str],
    block_events: List[BeatEvent],
    chord_pool: Dict[str, ChordDef],
    cfg: OptimizerConfig,
    is_first_block: bool = False,
    is_last_block: bool = False,
) -> List[float]:
    local_scores: List[float] = []
    prev_chord: Optional[ChordDef] = None

    for i, chord_name in enumerate(seq):
        chord = chord_pool[chord_name]
        event = block_events[i]

        local = local_chord_score(
            event=event,
            chord=chord,
            cfg=cfg,
            is_first_beat_of_piece=(is_first_block and i == 0),
            is_last_beat_of_piece=(is_last_block and i == len(seq) - 1),
        )

        if prev_chord is not None:
            local += functional_flow_score(prev_chord, chord, cfg)
            local += common_tone_score(prev_chord, chord, cfg)

        if i < len(seq) - 1:
            local += secondary_resolution_score(chord_name, seq[i + 1], cfg)

        local_scores.append(local)
        prev_chord = chord

    return local_scores


def _sequence_score_wrapper(
    seq: List[str],
    block_events: List[BeatEvent],
    chord_pool: Dict[str, ChordDef],
    cfg: OptimizerConfig,
) -> float:
    return score_chord_sequence(
        events=block_events,
        chord_names=seq,
        chord_pool=chord_pool,
        cfg=cfg,
    )


def _initialize_couplings(candidate_matrix: List[List[str]]) -> List[Dict[str, Dict[str, float]]]:
    """
    coupling_states[t][left][right] is the learned compatibility
    between slot t chord=left and slot t+1 chord=right.
    """
    couplings: List[Dict[str, Dict[str, float]]] = []

    for t in range(len(candidate_matrix) - 1):
        lefts = candidate_matrix[t]
        rights = candidate_matrix[t + 1]

        layer = {}
        for l in lefts:
            layer[l] = {r: 0.0 for r in rights}
        couplings.append(layer)

    return couplings


def _sample_sequence_with_coupling(
    weight_states: List[Dict[str, float]],
    coupling_states: List[Dict[str, Dict[str, float]]],
    rng: random.Random,
    coupling_strength: float,
    temperature: float,
) -> Tuple[List[str], float]:
    """
    Sample one sequence where the choice at time t depends on:
    - local superposition-like weight at t
    - coupling with previously chosen chord at t-1
    """
    seq: List[str] = []
    seq_probability = 1.0

    for t in range(len(weight_states)):
        base_dist = _normalize_weight_dict(weight_states[t])

        if t == 0:
            chosen = _sample_from_distribution(base_dist, rng)
            seq.append(chosen)
            seq_probability *= base_dist.get(chosen, 0.0)
            continue

        prev_chord = seq[-1]
        adjusted_scores = []
        candidates = list(base_dist.keys())

        for cand in candidates:
            base_p = max(1e-12, base_dist[cand])
            coupling_bonus = coupling_states[t - 1].get(prev_chord, {}).get(cand, 0.0)

            # log-prob + coupling acts as interference-like contextual update
            score = math.log(base_p) + coupling_strength * coupling_bonus
            adjusted_scores.append(score)

        adjusted_probs = _softmax(adjusted_scores, temperature=temperature)
        adjusted_dist = {cand: p for cand, p in zip(candidates, adjusted_probs)}

        chosen = _sample_from_distribution(adjusted_dist, rng)
        seq.append(chosen)
        seq_probability *= adjusted_dist.get(chosen, 0.0)

    return seq, seq_probability


# ============================================================
# Quantum-inspired solver with coupling
# ============================================================

def solve_block_quantum_inspired(
    block_events: List[BeatEvent],
    chord_pool: Dict[str, ChordDef],
    cfg: OptimizerConfig,
    block_index: int = 0,
    candidate_count: int = 8,
    iterations: int = 18,
    samples_per_iteration: int = 96,
    learning_rate: float = 0.18,
    temperature: float = 1.0,
    elite_fraction: float = 0.20,
    coupling_strength: float = 1.2,
    coupling_learning_rate: float = 0.25,
    random_seed: Optional[int] = None,
    is_first_block: bool = False,
    is_last_block: bool = False,
) -> QuantumBlockResult:
    """
    Quantum-inspired block solver with:
    - superposition-like per-slot weights
    - interference-like reinforcement/suppression
    - coupling between neighbouring slots (entanglement-like dependency)
    """
    if not block_events:
        raise ValueError("block_events cannot be empty")

    if iterations <= 0:
        raise ValueError("iterations must be > 0")
    if samples_per_iteration <= 0:
        raise ValueError("samples_per_iteration must be > 0")

    rng = random.Random() if random_seed is None else random.Random(random_seed + block_index)

    candidate_matrix = build_candidate_matrix(
        block_events=block_events,
        chord_pool=chord_pool,
        candidate_count=candidate_count,
    )

    # --------------------------------------------------------
    # 1) Initialize superposition-like states
    # --------------------------------------------------------
    weight_states: List[Dict[str, float]] = []
    for t, candidates in enumerate(candidate_matrix):
        init_scores = []
        for cand_name in candidates:
            chord = chord_pool[cand_name]
            init_scores.append(
                local_chord_score(
                    event=block_events[t],
                    chord=chord,
                    cfg=cfg,
                    is_first_beat_of_piece=(is_first_block and t == 0),
                    is_last_beat_of_piece=(is_last_block and t == len(candidate_matrix) - 1),
                )
            )
        probs = _softmax(init_scores, temperature=temperature)
        weight_states.append({cand: p for cand, p in zip(candidates, probs)})

    # --------------------------------------------------------
    # 2) Initialize coupling states
    # --------------------------------------------------------
    coupling_states = _initialize_couplings(candidate_matrix)

    best_seq: Optional[List[str]] = None
    best_score = -1e18
    best_probability = 0.0
    best_local_scores: List[float] = []
    history_best_scores: List[float] = []

    # --------------------------------------------------------
    # 3) Iterative refinement
    # --------------------------------------------------------
    for _ in range(iterations):
        sampled_sequences: List[Tuple[List[str], float, float]] = []

        for _sample_idx in range(samples_per_iteration):
            seq, seq_probability = _sample_sequence_with_coupling(
                weight_states=weight_states,
                coupling_states=coupling_states,
                rng=rng,
                coupling_strength=coupling_strength,
                temperature=temperature,
            )

            seq_score = _sequence_score_wrapper(
                seq=seq,
                block_events=block_events,
                chord_pool=chord_pool,
                cfg=cfg,
            )

            sampled_sequences.append((seq, seq_score, seq_probability))

            if seq_score > best_score:
                best_score = seq_score
                best_seq = seq[:]
                best_probability = seq_probability
                best_local_scores = _compute_local_scores_for_sequence(
                    seq=seq,
                    block_events=block_events,
                    chord_pool=chord_pool,
                    cfg=cfg,
                    is_first_block=is_first_block,
                    is_last_block=is_last_block,
                )

        sampled_sequences.sort(key=lambda x: x[1], reverse=True)
        history_best_scores.append(sampled_sequences[0][1])

        elite_count = max(1, int(round(samples_per_iteration * elite_fraction)))
        elite = sampled_sequences[:elite_count]
        low_tail = sampled_sequences[-elite_count:]

        mean_score = sum(score for _, score, _ in sampled_sequences) / len(sampled_sequences)
        max_score = max(score for _, score, _ in sampled_sequences)
        min_score = min(score for _, score, _ in sampled_sequences)
        score_span = max(1e-9, max_score - min_score)

        # -------------------------
        # Update local weights
        # -------------------------
        contributions: List[Dict[str, float]] = [
            {cand: 0.0 for cand in candidate_matrix[t]}
            for t in range(len(candidate_matrix))
        ]

        for seq, seq_score, _ in elite:
            adv = max(0.0, (seq_score - mean_score) / score_span)
            for t, chord_name in enumerate(seq):
                contributions[t][chord_name] += adv

        for seq, seq_score, _ in low_tail:
            pen = max(0.0, (mean_score - seq_score) / score_span)
            for t, chord_name in enumerate(seq):
                contributions[t][chord_name] -= pen

        for t in range(len(weight_states)):
            new_weights = {}
            for cand in weight_states[t]:
                old_w = weight_states[t][cand]
                delta = contributions[t][cand]
                new_w = old_w * math.exp(learning_rate * delta)
                new_weights[cand] = new_w
            weight_states[t] = _normalize_weight_dict(new_weights)

        # -------------------------
        # Update couplings
        # -------------------------
        for seq, seq_score, _ in elite:
            adv = max(0.0, (seq_score - mean_score) / score_span)
            for t in range(len(seq) - 1):
                left = seq[t]
                right = seq[t + 1]
                coupling_states[t][left][right] += coupling_learning_rate * adv

        for seq, seq_score, _ in low_tail:
            pen = max(0.0, (mean_score - seq_score) / score_span)
            for t in range(len(seq) - 1):
                left = seq[t]
                right = seq[t + 1]
                coupling_states[t][left][right] -= coupling_learning_rate * pen

    # --------------------------------------------------------
    # 4) Decode final solution
    # --------------------------------------------------------
    if best_seq is None:
        # fallback decode using local maxima with coupling-aware greedy decode
        decoded = []
        for t in range(len(weight_states)):
            if t == 0:
                chosen = max(weight_states[t], key=weight_states[t].get)
            else:
                prev = decoded[-1]
                candidates = list(weight_states[t].keys())
                scores = []
                for cand in candidates:
                    local = math.log(max(1e-12, weight_states[t][cand]))
                    coup = coupling_states[t - 1].get(prev, {}).get(cand, 0.0)
                    scores.append(local + coupling_strength * coup)
                chosen = candidates[max(range(len(candidates)), key=lambda i: scores[i])]
            decoded.append(chosen)

        best_seq = decoded
        best_score = _sequence_score_wrapper(
            seq=best_seq,
            block_events=block_events,
            chord_pool=chord_pool,
            cfg=cfg,
        )
        best_local_scores = _compute_local_scores_for_sequence(
            seq=best_seq,
            block_events=block_events,
            chord_pool=chord_pool,
            cfg=cfg,
            is_first_block=is_first_block,
            is_last_block=is_last_block,
        )
        best_probability = 1.0

    return QuantumBlockResult(
        start_beat=block_events[0].global_beat_index,
        end_beat=block_events[-1].global_beat_index,
        chords=best_seq,
        local_scores=best_local_scores,
        state_probability=best_probability,
        gamma=float(iterations),
        beta=float(learning_rate),
        metadata={
            "solver": "quantum_inspired_coupled",
            "block_index": block_index,
            "candidate_count": candidate_count,
            "iterations": iterations,
            "samples_per_iteration": samples_per_iteration,
            "learning_rate": learning_rate,
            "temperature": temperature,
            "elite_fraction": elite_fraction,
            "coupling_strength": coupling_strength,
            "coupling_learning_rate": coupling_learning_rate,
            "block_score": best_score,
            "history_best_scores": history_best_scores,
            "final_weight_states": weight_states,
            "final_coupling_states": coupling_states,
        },
    )