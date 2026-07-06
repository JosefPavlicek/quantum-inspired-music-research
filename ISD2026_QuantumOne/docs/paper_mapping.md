# Paper-to-Repository Mapping

This document maps the main concepts from the ISD 2026 paper to the repository implementation.

## Generative Harmonizer (Quantum-Inspired Module)

Paper concept: beat-level melody representation, overlapping melodic blocks, candidate chord generation, quantum-inspired candidate exploration.

Repository files:

- `advanced_quantum_harmonizer/musicxml_loader.py`
- `advanced_quantum_harmonizer/beat_representation.py`
- `advanced_quantum_harmonizer/candidate_selector.py`
- `advanced_quantum_harmonizer/quantum_block_solver.py`
- `advanced_quantum_harmonizer/scoring.py`
- `advanced_quantum_harmonizer/overlap_merger.py`
- `advanced_quantum_harmonizer/main.py`

## Rule-Based Optimizer

Paper concept: post-processing layer for reducing redundant chord changes, smoothing bass motion, adjusting chord complexity, and stabilizing cadences.

Repository files:

- `Harmonizer/musicxml_optimizer.py`
- `advanced_quantum_harmonizer/postprocessor.py`

## Dataset

Paper concept: 11 short monophonic MusicXML melodies.

Repository directory:

- `MusicLibrary/`

## Evaluation Metrics

Paper concept: structural metrics, reference-based metrics, and robustness metrics.

Repository files:

- `evaluation/evaluator.py`
- `evaluation/results.csv`
- `evaluation/results_extended.csv`
- `evaluation/description.txt`

## Generated Examples

Paper concept: raw and optimized MusicXML outputs.

Repository directory:

- `advanced_quantum_harmonizer/output/`
