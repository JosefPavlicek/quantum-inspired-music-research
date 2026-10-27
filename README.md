# Quantum-Inspired Music Research

**Author:** Josef Pavlíček  
**ORCID:** [0000-0002-3959-5406](https://orcid.org/0000-0002-3959-5406)  
**Research profiles:** [Google Scholar](https://scholar.google.com/citations?user=PXaXsPoAAAAJ) · [ResearchGate](https://www.researchgate.net/profile/Josef-Pavlicek)

This repository collects research software, experimental workflows, evaluation results, and reproducibility materials related to quantum-inspired music generation, automatic melody harmonization, harmonic analysis, explainable computational music systems, and music education.

The research focuses on the **computational representation of human harmonic decision-making**, with particular attention to transparent algorithms, interpretable harmonic alternatives, and human-centered music generation.

## Current Projects

### ISD2026_QuantumOne

A hybrid quantum-inspired system for **automatic music harmonization from melody**.

The system combines:

- Beat-level melodic analysis
- Overlapping harmonic blocks
- Quantum-inspired candidate exploration
- Rule-based harmonic optimization
- MusicXML export and quantitative evaluation

This research artifact accompanies the ISD 2026 paper:

**Designing Maintainable Hybrid Generative Systems: A Quantum-Inspired Approach to Automated Music Harmony Generation**

**Repository directory:** [`ISD2026_QuantumOne/`](ISD2026_QuantumOne/)

---

### Explainable Melody Harmonizer (EMH)

A transparent and reproducible system for **automatic harmonization of monophonic melodies using explicit harmonic decision criteria and Viterbi-like dynamic programming**.

Unlike the quantum-inspired approach, EMH explicitly represents harmonic alternatives, evaluates their musical properties, and selects a globally coherent chord sequence using interpretable scoring components.

The system processes melody without requiring access to a reference chord progression.

#### Main Capabilities

- Automatic tonal-context estimation from melody
- Meter-aware and duration-aware melodic analysis
- Explicit diatonic chord candidate generation
- Melody–chord compatibility scoring
- Harmonic-function and transition scoring
- Harmonic persistence and cadence modeling
- Global Viterbi-like sequence optimization
- Inspectable harmonic decisions and alternative candidates
- JSON and CSV diagnostic outputs
- Reproducible experimental configurations

The frozen EMH v0.12 harmonic model uses a restricted candidate vocabulary and fixed scoring weights. This provides a controlled baseline for evaluating its harmonic decisions without adapting the model to the reference arrangements.

#### Research Applications

**1. Human-Centered Harmonic Decision-Making**

The first AHFE 2026 study investigates how a computational harmonization model preserves, transforms, or differs from harmonic decisions associated with individual human-created songs and their narrative contexts.

Paper:

**From Human Narrative to Harmonic Structure: A Human-Centered Investigation of Algorithmic Music Generation through the Chord Wheel Diagram**

This study establishes the case-based foundation for investigating human and computational harmonic decision-making.

**2. Corpus-Based Evaluation on HookTheory**

The follow-up AHFE 2026 study extends the evaluation to independently collected human chord annotations from the HookTheory corpus, distributed through the SheetSage project.

Paper:

**From Individual Songs to Music Corpora: Evaluating Explainable Harmonic Decision-Making on HookTheory**

The experiment evaluates a frozen EMH model on 19 selected HookTheory excerpts, comprising 439 evaluable harmonic segments.

Key results:

| Evaluation measure | Result |
|---|---:|
| Exact chord agreement | 90 / 439 (20.50%) |
| Chord-root agreement | 139 / 439 (31.66%) |
| Harmonic-function agreement (EMH-inferred key) | 200 / 420 (47.62%) |
| Candidate chord coverage | 236 / 439 (53.76%) |
| Candidate root coverage | 420 / 439 (95.67%) |
| Chord agreement given candidate coverage | 90 / 236 (38.14%) |
| Root agreement on unmixed segments | 125 / 399 (31.33%) |

The decision-level diagnostic distinguishes three mutually exclusive outcomes:

- **90 segments (20.50%)**: The generated chord matches the human reference.
- **203 segments (46.24%)**: The reference chord is unavailable in the model's candidate vocabulary.
- **146 segments (33.26%)**: The reference chord is available but another candidate is selected.

An additional post-hoc tonal-context audit found exact agreement between EMH-inferred keys and HookTheory key annotations in **8 of 19 excerpts (42.1%)**.

These results help distinguish chord-representation limitations, alternative selection decisions, and tonal-context discrepancies. The three diagnostic dimensions are not mutually exclusive.

The reported agreement measures describe correspondence with the annotated reference, not subjective musical quality or the correctness of a unique harmonization. Educational and human–AI collaboration benefits are potential applications rather than outcomes validated through user studies.

#### Experimental Integrity and Reproducibility

Human-reference chords are excluded from harmonic generation and used only for post-hoc evaluation.

The corpus experiment preserves the EMH v0.12 model and its decision rules. HookTheory-specific loading, adaptation, evaluation, and diagnostic auditing are implemented separately from the frozen harmonic generator.

**Reproducible experimental release:**

`emh-v0.12.1-hooktheory`

The release identifies the frozen HookTheory experiment. Subsequent diagnostic additions do not alter the original experimental baseline.

**Repository directory:** [`Explainable_Melody_Harmonizer/`](Explainable_Melody_Harmonizer/)

See the README in that directory for installation, MusicXML examples, HookTheory evaluation procedures, experimental commands, and reproducibility instructions.

---

### HARMONIX – Structural Constraints in Knowledge-Guided Generative Systems

HARMONIX extends the Explainable Melody Harmonizer research into a **systems-engineering investigation of explicit domain constraints**. Musical harmonization serves as a structured experimental testbed for a broader question: when do interpretable rules improve agreement with human-created reference solutions, and when do they interfere with legitimate context-dependent transformations?

HARMONIX uses a deterministic, Viterbi-style optimization engine and compares four controlled configurations:

- **Corrected EMH:** corrected optimization baseline without the additional structural constraints.
- **R (Repetition):** adds a repetition-consistency constraint (weight 0.12).
- **F (Function):** adds a harmonic-function constraint (weight 0.06).
- **RF (Combined):** applies both constraints with the same fixed weights.

All four configurations use the same search mechanism. The experiment therefore evaluates **the effects of constraint design**, not competing optimization algorithms. The original EMH source is retained as a separate, frozen snapshot to preserve experimental provenance.

#### Evaluation and Main Findings

The current v0.19 diagnostic evaluation includes **17,911 successfully processed TRAIN records** and **1,821 VALID records**, with **131,117** and **12,517** evaluated motif pairs, respectively. The analysis compares generated chord-root relationships with human-reference relationships across stable, changed, and transposed melodic contexts.

| Context | RF vs. Corrected EMH (TRAIN) | RF vs. Corrected EMH (VALID) |
|---|---:|---:|
| Untransposed motif; reference root unchanged | +5.08 pp | +5.00 pp |
| Untransposed motif; reference root changed | −1.52 pp | −0.99 pp |
| Transposed motif; reference harmony follows transposition | −8.80 pp | −8.93 pp |
| Transposed motif; reference harmony does not follow transposition | +4.13 pp | +4.18 pp |

The results show a **context-dependent trade-off**: explicit structural constraints can improve agreement where relationships remain stable, yet reduce agreement where the reference requires transformation. Effects have consistent directions across TRAIN and VALID; they should not be interpreted as proof of generalization beyond the evaluated corpus. Aggregate exact-chord agreement changes are small, so the main contribution concerns **structural decision behavior**, not an overall improvement in chord-prediction accuracy.

The systems-engineering implication is that constraints may require **context-sensitive applicability or weighting** rather than unconditional enforcement. Such an adaptive mechanism is a proposed design direction, **not an implemented or experimentally validated HARMONIX feature**.

#### Reproducibility and Data Access

The project includes source code, configurations, tests, evaluation procedures, and diagnostic outputs as documented in its own README. Human-reference annotations originating from **HookTheory / SheetSage** are third-party data and are **not redistributed** as part of this repository. Researchers must obtain access from the original data provider under the applicable terms before reproducing corpus-based experiments. The reference annotations are used for post-hoc evaluation, not as inputs to harmonic generation.

**Repository directory:** [`HARMONIX/`](HARMONIX/)

See [`HARMONIX/README.md`](HARMONIX/README.md) for installation, execution, output locations, dataset preparation, metrics, and version-specific reproducibility instructions.

---

## Research Focus

The repository supports a continuing research programme connecting computational models of harmony with explainable decision-making and human musical interpretation.

The principal research areas include:

- Quantum-inspired music generation and optimization
- Automatic melody harmonization
- Explainable and interpretable music generation
- Computational modeling of harmonic decision-making
- Tonal context, harmonic function, and chord progression analysis
- Corpus-based evaluation of generative music systems
- Human-centered AI and human–AI musical co-creation
- Music education and the exploration of harmonic alternatives
- Reproducible computational music research
- Constraint applicability, structural consistency, and context-sensitive decision optimization

The broader objective is to move beyond generating plausible chord progressions toward understanding **which harmonic decisions a computational system makes, which alternatives it considers, why its choices differ from human references, and how those differences can be meaningfully examined by people**.

## Data and Reproducibility

Experimental code, configurations, evaluation procedures, and selected research artifacts are organized within their corresponding project directories.

External datasets, including HookTheory annotations distributed through SheetSage, remain subject to their original licensing and distribution terms.

Research outputs should be interpreted in the context of their documented experimental versions, eligibility criteria, and evaluation limitations.
