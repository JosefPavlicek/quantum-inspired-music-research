# ISD2026 QuantumOne

This repository contains the research prototype accompanying the ISD 2026 paper:

**Designing Maintainable Hybrid Generative Systems: A Quantum-Inspired Approach to Automated Music Harmony Generation**

The **full version of the paper** is available on arXiv:

[**Designing Maintainable Hybrid Generative Systems: A Quantum-Inspired Approach to Automated Music Harmony Generation**](https://arxiv.org/pdf/2607.06296)

The project implements an automated music harmony generation pipeline based on a melody input in MusicXML format. It combines a quantum-inspired candidate exploration module with a rule-based post-processing optimizer and an evaluation pipeline used to compute the metrics reported in the paper.

## Repository structure

```text
QuantumOne-ISD2026/
├── advanced_quantum_harmonizer/     # Main quantum-inspired harmonization pipeline
│   ├── main.py                      # Batch runner for MusicLibrary inputs
│   ├── musicxml_loader.py           # MusicXML melody parser
│   ├── beat_representation.py       # Beat-level melody representation
│   ├── candidate_selector.py        # Candidate chord selection
│   ├── quantum_block_solver.py      # Quantum-inspired block-level candidate exploration
│   ├── scoring.py                   # Musical scoring functions
│   ├── overlap_merger.py            # Merging of overlapping melodic/harmonic blocks
│   ├── postprocessor.py             # Internal post-processing of generated chords
│   ├── exporter.py                  # MusicXML export preserving the melody
│   ├── transposition.py             # Key detection and transposition support
│   ├── config.py                    # Experiment configuration
│   └── output/                      # Generated raw and optimized MusicXML examples
│
├── Harmonizer/
│   └── musicxml_optimizer.py        # Rule-based optimizer used after raw generation
│
├── MusicLibrary/                    # MusicXML melodies used in the ISD 2026 experiment
│   ├── Autumn-Leaves.xml
│   ├── Country_Roads.musicxml
│   ├── Folsom_Prison_Blues.musicxml
│   ├── It-s-a-Long-Way-to-Tipperary.xml
│   ├── Ovcaci-Ctveraci.xml
│   ├── Quantum-song-I.xml
│   ├── Quantum-song-II.xml
│   ├── Quantum-song-III.xml
│   ├── Quantum-song-IV.xml
│   ├── Quantum-song-V.xml
│   └── fly-me-to-the-moon-frank-sinatra.xml
│
├── evaluation/
│   ├── evaluator.py                 # Structural and reference-based evaluator
│   ├── results.csv                  # Evaluation summary
│   ├── results_extended.csv         # Extended evaluation output
│   └── description.txt              # Description of evaluation metrics
│
├── docs/
│   └── paper_mapping.md             # Mapping between the paper and repository artifacts
│
├── requirements.txt
└── .gitignore
```

## Main pipeline

The core pipeline is implemented in `advanced_quantum_harmonizer/`.

It performs the following steps:

1. Load a monophonic melody from MusicXML.
2. Normalize and optionally transpose the melody to C major.
3. Convert the melody into a beat-level representation.
4. Split the melody into overlapping melodic blocks.
5. Generate candidate chords for each beat.
6. Solve overlapping blocks using a quantum-inspired candidate exploration procedure.
7. Merge block-level harmonic solutions.
8. Export the raw harmonized MusicXML.
9. Apply the rule-based optimizer and export the optimized MusicXML.

The implementation is quantum-inspired: it uses concepts such as weighted candidate states, superposition-like representations, and interference-like reinforcement of high-scoring candidates. It does **not** require quantum hardware.

## Running the harmonizer

Recommended environment:

```bash
python --version   # Python 3.11+ recommended
```

Run the batch harmonization pipeline from the repository root:

```bash
python -m advanced_quantum_harmonizer.main
```

This processes all MusicXML files in `MusicLibrary/` and writes raw and optimized outputs to:

```text
advanced_quantum_harmonizer/output/
```

## Running the evaluator

Evaluate all generated outputs:

```bash
python evaluation/evaluator.py \
  --glob "advanced_quantum_harmonizer/output/*.musicxml" \
  --csv evaluation/results_new.csv
```

The evaluator reports structural metrics such as chord density, average chord duration, redundancy ratio, bass jump, and segment length standard deviation. It also computes reference-based metrics by comparing generated harmonies with the reference harmonizations stored in `MusicLibrary/`.

## Dataset

The dataset consists of 11 short monophonic melodies represented in MusicXML format:

- 2 jazz standards
- 2 country-style melodies
- 2 folk melodies
- 5 original test melodies designed for controlled harmonic evaluation

The melodies are used as representative harmonic situations rather than as a random statistical sample.

## Relation to the ISD 2026 paper

This repository supports the reproducibility of the ISD 2026 paper by providing:

- the implementation of the quantum-inspired generative harmonizer,
- the rule-based optimization layer,
- the MusicXML input melodies,
- example generated harmonizations,
- the evaluator used to compute the reported metrics.

## Notes and limitations

This repository is a research prototype. It is intended for reproducibility, inspection, and further experimentation rather than production use.

The optimizer is implemented as a separate post-processing script in `Harmonizer/musicxml_optimizer.py`, because the paper evaluates both the raw generator and the optimized generator as separate system variants.
