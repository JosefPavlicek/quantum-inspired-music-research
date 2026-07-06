# overlap_merger.py

from typing import List

from .quantum_block_solver import QuantumBlockResult


def merge_two_blocks(
    prev_result: QuantumBlockResult,
    next_result: QuantumBlockResult,
    overlap: int = 2,
) -> QuantumBlockResult:
    if overlap < 0:
        raise ValueError("overlap must be >= 0")

    if overlap == 0:
        merged_chords = prev_result.chords + next_result.chords
        merged_scores = prev_result.local_scores + next_result.local_scores
    else:
        if len(prev_result.chords) < overlap or len(next_result.chords) < overlap:
            raise ValueError("One of the blocks is shorter than overlap")

        merged_chords = prev_result.chords[:-overlap]
        merged_scores = prev_result.local_scores[:-overlap]

        for i in range(overlap):
            prev_ch = prev_result.chords[-overlap + i]
            next_ch = next_result.chords[i]

            prev_sc = prev_result.local_scores[-overlap + i] if prev_result.local_scores else 0.0
            next_sc = next_result.local_scores[i] if next_result.local_scores else 0.0

            if prev_ch == next_ch:
                merged_chords.append(prev_ch)
                merged_scores.append(max(prev_sc, next_sc))
            else:
                if prev_sc >= next_sc:
                    merged_chords.append(prev_ch)
                    merged_scores.append(prev_sc)
                else:
                    merged_chords.append(next_ch)
                    merged_scores.append(next_sc)

        merged_chords.extend(next_result.chords[overlap:])
        if next_result.local_scores:
            merged_scores.extend(next_result.local_scores[overlap:])

    return QuantumBlockResult(
        start_beat=min(prev_result.start_beat, next_result.start_beat),
        end_beat=max(prev_result.end_beat, next_result.end_beat),
        chords=merged_chords,
        local_scores=merged_scores,
        state_probability=max(prev_result.state_probability, next_result.state_probability),
        gamma=next_result.gamma,
        beta=next_result.beta,
        metadata={
            "merged_from": [
                prev_result.metadata.get("block_index"),
                next_result.metadata.get("block_index"),
            ]
        },
    )


def merge_block_results(
    block_results: List[QuantumBlockResult],
    overlap: int = 2,
) -> QuantumBlockResult:
    if not block_results:
        raise ValueError("block_results cannot be empty")

    merged = block_results[0]
    for nxt in block_results[1:]:
        merged = merge_two_blocks(merged, nxt, overlap=overlap)

    return merged