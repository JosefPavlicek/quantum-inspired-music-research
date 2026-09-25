# Quantum-Inspired Music Research

This repository collects public research artifacts related to quantum-inspired music generation, melody harmonization, harmonic analysis, explainable computational music systems, and music education.

## Current projects

### ISD2026_QuantumOne

A hybrid quantum-inspired harmonization system for **automatic music harmony generation from melody**.

The system combines:

- beat-level melodic analysis,
- overlapping harmonic blocks,
- quantum-inspired candidate exploration,
- rule-based harmonic optimization,
- MusicXML export and evaluation.

This artifact accompanies the ISD 2026 paper:

**Designing Maintainable Hybrid Generative Systems: A Quantum-Inspired Approach to Automated Music Harmony Generation**

Repository folder:

- `ISD2026_QuantumOne/`

---

### AHFE2026 Explainable Melody Harmonizer (EMH)

A transparent and reproducible system for **automatic music harmony generation from monophonic melody using Viterbi-like dynamic programming**. It was prepared for the paper name **From Human Narrative to Harmonic Structure: A Human-Centered Investigation of Algorithmic Music Generation through Chord-Wheel Analysis**

Unlike the quantum-inspired approach, EMH represents harmonic decisions explicitly. It analyzes the melody, detects its tonal context, divides it into meter-aware harmonic decision segments, evaluates possible chord candidates using interpretable scoring components, and searches for a globally coherent harmonic sequence.

The system provides:

- automatic key detection from melody,
- meter-aware and duration-aware melody analysis,
- explicit diatonic chord candidates,
- melody–chord compatibility scoring,
- functional harmonic transition scoring,
- harmonic persistence and cadence modeling,
- global Viterbi-like / dynamic-programming optimization,
- explainable alternatives for individual harmonic decisions,
- JSON and CSV decision logs,
- reproducible experimental configuration.

Reference/original harmony contained in experimental MusicXML files is not used during harmony generation. It is retained only for later post-hoc comparison with human harmonic decisions.

Repository folder:

- `Explainable_Melody_Harmonizer/`

See the README inside this folder for installation, experimental MusicXML examples, and instructions for running the harmonizer.

## Research focus

The repository hosts code, datasets, evaluation scripts, experimental inputs, generated outputs, and supplementary materials for research in:

- quantum-inspired music generation,
- automatic melody harmonization,
- explainable harmonic generation,
- harmonic analysis,
- computational representation of human harmonic decision-making,
- computational music systems,
- music education and explainable generative models.
