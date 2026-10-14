# Explainable Melody Harmonizer (EMH)

Transparent, reproducible, and explainable automatic harmony generation from monophonic melody, with MusicXML experiments and a separate HookTheory corpus-evaluation workflow.

EMH generates a harmonic sequence from a melody using explicit music-theoretical scoring and a global Viterbi-like dynamic-programming optimization. In addition to the selected chords, it exports a detailed decision log that makes the individual harmonic decisions inspectable and reproducible.

## Research context

EMH was designed as an explainable baseline for the research line:

> Computational representation of human harmonic decision-making: from formal models and explainable generation to education and human musical intention.

EMH is a separate approach alongside the existing quantum-inspired harmonizer in this repository. It is not its replacement.

The system supports two complementary experimental settings: six case-based MusicXML harmonizations and a frozen-model evaluation on selected HookTheory excerpts. Both preserve a strict separation between generation and post-hoc comparison with human/reference chords.

## Research artifacts and publications

**Case-based AHFE 2026 study:** *From Human Narrative to Harmonic Structure: A Human-Centered Investigation of Algorithmic Music Generation through the Chord Wheel Diagram*. This study investigates individual songs and the relationship between generated harmony and human harmonic decisions.

**HookTheory corpus AHFE 2026 study:** *From Individual Songs to Music Corpora: Evaluating Explainable Harmonic Decision-Making on HookTheory*. This follow-up evaluates the unchanged EMH v0.12 model against independently collected chord annotations.

The HookTheory experimental baseline is identified by the Git tag `emh-v0.12.1-hooktheory`. The tag identifies a reproducible software/experiment snapshot, **not a new harmonic decision model**. Post-hoc diagnostics added later should be committed separately without moving or rewriting that tag.

## Quick start

All commands in this README should be executed from the project directory:

```text
Explainable_Melody_Harmonizer/
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Verify the implementation:

```bash
python -m pytest -q
```

Run the harmonizer on a MusicXML file:

```bash
python harmonizer.py \
  --input examples/INPUT_FILE \
  --output results
```

For example:

```bash
python harmonizer.py \
  --input examples/Blowin-In-The-Wind.xml \
  --output results
```

The generated files are written to:

```text
results/
```

The six case-based experimental MusicXML files are stored in:

```text
examples/
```

Exact commands for reproducing every experimental run are provided below.

## Core principles

- Input is a monophonic MusicXML melody.
- Reference/original harmony does not influence generation.
- The global key is detected from melodic pitch content.
- Harmonic segmentation respects meter and note duration.
- The MusicXML core handles supported compound meters according to their natural pulse structure; the HookTheory adapter has a separate time-base validation requirement.
- Chord candidates are explicit rather than hidden in a black-box model.
- Harmonic decisions are evaluated using interpretable scoring components.
- The complete chord sequence is optimized globally using a Viterbi-like dynamic-programming procedure.
- Selected chords and alternative candidates are preserved in the decision log.
- Experimental parameters remain fixed between songs.
- The same input and configuration produce a reproducible result.

## Processing pipeline

The EMH generation pipeline is:

```text
MusicXML melody
    ↓
temporal representation
    ↓
melody-based key detection
    ↓
meter-aware harmonic segmentation
    ↓
chord candidate generation
    ↓
explicit candidate scoring
    ↓
global Viterbi-like optimization
    ↓
explainable decision log
```

Human/reference harmony is used only after this generation pipeline has finished, in a separate post-hoc evaluation stage.

## MusicXML input

The harmonizer works with monophonic melodic material stored in MusicXML.

The loader extracts musical information required by the algorithm, including:

- pitch,
- pitch class,
- onset,
- note duration,
- rests,
- measure position,
- beat position,
- meter,
- metric strength,
- MusicXML key metadata.

Internally, temporal values are represented exactly rather than relying on approximate floating-point timing.

MusicXML files may also contain original/reference `<harmony>` elements. These may remain in the experimental files so that the original human harmony is preserved for later evaluation. They are deliberately ignored by the generation pipeline.

## Key detection

EMH performs melody-based global key detection before generating chord candidates.

The detector evaluates all 24 major/minor tonalities:

- 12 major keys,
- 12 minor keys.

It uses a duration-weighted pitch-class distribution and major/minor tonal profiles. Candidate keys are ranked using correlation scores.

The highest-ranked detected key is used by the harmonizer. The MusicXML key signature is retained as metadata so that the notated key and melody-derived key can later be compared.

The key-detection output contains the complete ranking rather than only the winning key. This is important because some melodies can be tonally ambiguous.

The key-detection score is a correlation score and must not be interpreted as a probability.

## Harmonic segmentation

EMH does not automatically assign one chord to every note or every quarter note.

Instead, the melody is divided into harmonic decision segments according to meter. Notes within each segment contribute according to their duration and metric position.

Supported meters are:

- 2/4
- 3/4
- 4/4
- 6/8
- 12/8

The current segmentation uses the following decision grid:

- **2/4** – one harmonic segment per measure,
- **3/4** – one harmonic segment per measure,
- **4/4** – two harmonic segments per measure (beats 1–2 and 3–4),
- **6/8** – two natural dotted-quarter pulse segments,
- **12/8** – four natural dotted-quarter pulse segments.

Compound meters remain compound meters. For example, 12/8 is not converted to 6/4.

A harmonic decision segment therefore represents a musically defined time interval rather than an individual note.

## Chord candidates

For the detected key, EMH constructs an explicit candidate set based on diatonic harmony.

The baseline candidate vocabulary contains the diatonic functions:

- I
- ii
- iii
- IV
- V
- vi
- vii°

and selected common seventh-chord variants, including:

- ii7
- V7
- viiø7

The exact candidate vocabulary is deliberately limited and transparent. Consequently, a human reference chord can occasionally lie outside the available candidate space. Such cases are treated as an experimental limitation rather than being used to tune the generator to a particular song.

## Explicit harmonic scoring

Each chord candidate is evaluated using interpretable components.

The baseline includes:

- **melody–chord compatibility** – how well the melodic tones in the segment fit the candidate chord,
- **functional transition** – preference for musically meaningful harmonic-function movement,
- **persistence** – preference controlling unnecessary harmonic changes,
- **cadence** – preference for appropriate phrase/final resolution,
- **metric and duration weighting** – contribution of melodic tones according to duration and metric importance.

The scoring components are combined using fixed weights defined by the experimental configuration.

The current frozen baseline uses:

- melody compatibility: `0.50`
- functional transition: `0.25`
- persistence: `0.10`
- cadence: `0.15`

These values are model hyperparameters. They are not probabilities and are not claimed to be directly derived from the literature.

They must not be changed between experimental songs.

## Melody–chord compatibility

Within a harmonic segment, melodic tones are weighted by their duration and metric importance.

The baseline compatibility values are:

- chord tone: `1.0`
- diatonic non-chord tone: `0.45`
- chromatic tone: `0.0`

The resulting compatibility component summarizes how well a candidate chord supports the melodic content of the segment.

## Harmonic functions

The model uses explicit functional categories to evaluate harmonic movement.

The main functional groups are:

- **Tonic** – primarily I, vi, and contextually iii,
- **Predominant** – primarily ii and IV,
- **Dominant** – primarily V and vii°.

Functional transition scoring contributes to the global preference for coherent harmonic movement.

## Global Viterbi-like optimization

EMH does not use a greedy procedure that independently chooses the locally highest-scoring chord in each segment.

Instead, the complete harmonic sequence is optimized using dynamic programming in a Viterbi-like search.

For every segment and chord candidate, the algorithm considers:

1. the local evidence for the chord,
2. its relationship to the preceding harmonic state,
3. the accumulated score of the harmonic path.

The final output is therefore the highest-scoring complete path under the model rather than a sequence of independent local decisions.

This distinction is important when interpreting the decision log: a selected chord can be part of the globally preferred path even when another candidate appears locally competitive at a particular intermediate segment.

The exported `path_score` is an accumulated prefix score. Alternative candidates shown at an intermediate segment should therefore not be interpreted as complete suffix-aware alternative harmonizations.

## Rests and silent segments

A segment containing no melodic evidence does not independently introduce a new harmony.

For rest-only segments, the frozen baseline preserves the preceding harmonic state. This prevents arbitrary chord changes caused solely by the absence of melody.

## Explainability and decision log

For each selected harmonic segment, EMH records information including:

- segment number,
- measure,
- starting beat,
- segment duration,
- selected chord,
- Roman numeral,
- harmonic function,
- melody–chord compatibility,
- functional-transition score,
- persistence score,
- cadence score,
- local score,
- accumulated path score,
- alternative chord candidates.

This makes it possible to inspect not only **what** harmony was generated, but also the computational evidence contributing to each decision.

## Project structure

- `harmonizer.py` – command-line entry point
- `config.yaml` – model parameters
- `emh/model.py` – internal data structures
- `emh/musicxml_loader.py` – MusicXML parsing
- `emh/key_detection.py` – melody-based global key detection
- `emh/meter.py` – meter and metric-strength logic
- `emh/segmentation.py` – harmonic decision grid
- `emh/harmony.py` – chord candidate generation
- `emh/scoring.py` – explicit scoring components
- `emh/optimizer.py` – global DP/Viterbi optimization
- `emh/explanation.py` – JSON/CSV decision log
- `emh/pipeline.py` – complete harmonization pipeline
- `emh/musicxml_writer.py` – generated harmony output support
- `tests/` – unit tests and MusicXML fixtures
- `examples/` – experimental MusicXML inputs
- `results/` – generated experimental outputs

## Installation

Python 3.11 or newer is recommended.

From the repository root, first enter the EMH directory:

```bash
cd Explainable_Melody_Harmonizer
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Running the regression tests

Before reproducing the musical experiments, verify the implementation using the automated regression test suite.

Run:

```bash
python -m pytest -q
```

Use `python -m pytest -q` rather than plain `pytest -q` to ensure that the local `emh` package is resolved consistently in the execution environment.

The regression suite tests the implementation itself. It is separate from the six MusicXML experiments and the HookTheory corpus evaluation described below.

## Case-based MusicXML experiments

The following six-song workflow is the original case-based experiment. It is separate from the HookTheory TEST-partition corpus experiment.

### Experimental MusicXML dataset

The experimental MusicXML inputs are stored in:

```text
examples/
```

The current frozen dataset contains six melodies:

1. Bob Dylan – *Blowin' in the Wind*  
   `Blowin-In-The-Wind.xml`

2. Bob Dylan – *Tangled Up in Blue*  
   `Tangled-Up-in-Blue.xml`

3. Johnny Cash – *I Walk the Line*  
   `I-WalkThe-Line-melody-line.xml`

4. Johnny Cash – *Folsom Prison Blues*  
   `Folsom-Prison-Blues.xml`

5. Ritchie Valens – *Donna*  
   `Donna-Valens.musicxml`

6. Ritchie Valens – *La Bamba*  
   `LaBamba_melody.musicxml`

Some files may also contain duplicate notation/TAB material or original/reference harmony. The generation pipeline uses the intended monophonic melodic material and does not use the reference harmony as evidence for chord generation.

## Running the experimental melodies

All commands below must be executed from:

```text
Explainable_Melody_Harmonizer/
```

The general command is:

```bash
python harmonizer.py \
  --input examples/INPUT_FILE \
  --output results
```

Replace `INPUT_FILE` with the exact MusicXML filename.

Each melody is processed independently. The following commands reproduce the six experimental harmonization runs.

### 1. Blowin' in the Wind – Bob Dylan

```bash
python harmonizer.py \
  --input examples/Blowin-In-The-Wind.xml \
  --output results
```

### 2. Tangled Up in Blue – Bob Dylan

```bash
python harmonizer.py \
  --input examples/Tangled-Up-in-Blue.xml \
  --output results
```

### 3. I Walk the Line – Johnny Cash

```bash
python harmonizer.py \
  --input examples/I-WalkThe-Line-melody-line.xml \
  --output results
```

### 4. Folsom Prison Blues – Johnny Cash

```bash
python harmonizer.py \
  --input examples/Folsom-Prison-Blues.xml \
  --output results
```

### 5. Donna – Ritchie Valens

```bash
python harmonizer.py \
  --input examples/Donna-Valens.musicxml \
  --output results
```

### 6. La Bamba – Ritchie Valens

```bash
python harmonizer.py \
  --input examples/LaBamba_melody.musicxml \
  --output results
```

## Reproducing the six-song MusicXML experiment

To reproduce the complete experiment from a clean installation:

### Step 1 – enter the project directory

```bash
cd Explainable_Melody_Harmonizer
```

### Step 2 – install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 – verify the frozen implementation

```bash
python -m pytest -q
```

### Step 4 – generate harmony for each experimental melody

Run the six commands listed in the section **Running the experimental melodies**.

Each song must be processed independently using the same source code and the same configuration.

### Step 5 – inspect the generated files

Generated outputs are stored in:

```text
results/
```

### Step 6 – perform post-hoc evaluation

Only after generation has finished may the generated harmony be compared with the original/reference harmony.

The experimental procedure is therefore:

1. Verify the frozen EMH implementation using the regression test suite.
2. Process each MusicXML melody independently.
3. Store generated outputs in `results/`.
4. Do not modify model parameters between songs.
5. Do not use original/reference harmony during generation.
6. Perform comparison with human/reference harmony only after the generated results have been produced.

This procedure is essential because EMH is evaluated as a **frozen explainable baseline**. Parameters must not be adjusted in response to the result of an individual song.

## Generated results

For each experimental input, EMH writes machine-readable outputs to:

```text
results/
```

The principal output files are:

- `*_decisions.csv` – tabular harmonic decision log,
- `*_decisions.json` – complete harmonic decision log including alternatives,
- `*_key_detection.json` – detected key, correlation score, XML key metadata, and ranking of alternative keys.

For example, processing:

```text
Blowin-In-The-Wind.xml
```

produces outputs following the naming pattern:

```text
Blowin-In-The-Wind_decisions.csv
Blowin-In-The-Wind_decisions.json
Blowin-In-The-Wind_key_detection.json
```

The decision logs preserve the generated harmony together with the intermediate evidence needed to inspect individual decisions.

## Experimental firewall

The separation between generated and reference harmony is a central methodological requirement of EMH.

Reference/original harmony must **not influence harmony generation**.

Experimental MusicXML files may physically contain `<harmony>` elements because the same files preserve the human/reference harmony required for later evaluation.

These `<harmony>` elements are ignored by the generation pipeline. They are not used for:

- melody-based key detection,
- harmonic segmentation,
- chord candidate generation,
- candidate scoring,
- functional-transition scoring,
- Viterbi optimization.

The generator therefore receives melodic evidence and configuration, while reference harmony remains unavailable to the harmonic decision process.

Reference harmony belongs exclusively to the separate **post-hoc evaluation stage**.

This distinction prevents reference-harmony leakage and makes it possible to compare generated and human harmonic decisions without allowing the human solution to influence generation.

## Reproducibility and frozen baseline

The experimental EMH implementation is treated as a frozen baseline.

The following aspects must remain unchanged across the six MusicXML experiments and the frozen HookTheory corpus evaluation:

- key-detection method,
- segmentation rules,
- chord candidate vocabulary,
- melody-compatibility rules,
- scoring weights,
- harmonic-function transition rules,
- persistence handling,
- cadence handling,
- rest handling,
- deterministic tie-breaking,
- Viterbi-like optimization procedure.

The model must not be tuned after inspecting the reference harmony or the result of an individual song.

A genuine software defect may be corrected, but such a correction should be documented as a new software version rather than silently changing the experimental baseline.

## Current experimental version

The frozen harmonic model is **EMH v0.12**. The HookTheory corpus experiment is preserved under the Git tag **`emh-v0.12.1-hooktheory`**. The latter is a release identifier, not a different model or a tuning step.

The version includes:

- MusicXML melody loading,
- exact temporal representation,
- meter-aware segmentation,
- major and minor key detection from melody,
- explicit diatonic chord candidates,
- selected seventh-chord variants,
- duration- and metric-aware melody compatibility,
- functional harmonic transition scoring,
- persistence scoring,
- cadence scoring,
- rest-only segment handling,
- deterministic tie-breaking,
- global Viterbi-like optimization,
- JSON and CSV explainability output,
- key-detection metadata and ranking.

## Scope and limitations

EMH is intentionally designed as a transparent baseline rather than an unrestricted style-learning system.

Important limitations include:

- global key detection rather than modulation tracking,
- a deliberately limited candidate chord vocabulary,
- no neural-network or black-box style model,
- no training corpus,
- fixed meter-dependent segmentation,
- no assumption that the original human chord is the only musically valid solution.

These limitations are part of the experimental design. They make the model easier to inspect and allow disagreements between generated and human harmony to be categorized rather than hidden.

A difference from the human reference can, for example, result from:

- tonal ambiguity in the melody,
- a human chord outside the candidate vocabulary,
- different harmonic rhythm,
- locally ambiguous melody–chord compatibility,
- the preference of the global harmonic path over a locally attractive candidate.

For this reason, subsequent evaluation should not be reduced to exact chord matching alone.

## HookTheory corpus evaluation (AHFE 2026 follow-up)

### Purpose and frozen-model design

The corpus experiment tests whether the **same frozen EMH v0.12 decision rules** used for individual songs can be evaluated against independently collected human harmony annotations. The HookTheory symbolic corpus is distributed through the SheetSage project; original dataset access and reuse are governed by its upstream terms.

The evaluation uses a deterministic selection manifest from the HookTheory **TEST partition**. Twenty excerpts were selected, **19 were processed**, and **one was excluded** because compound-meter time-base mapping had not been verified in the HookTheory adapter. The resulting sample contains **439 evaluable harmonic decision segments**. This is a selected proof-of-concept sample, not a representative estimate of performance across all popular music.

The frozen candidate set contains seven diatonic triads (`I`, `ii`, `iii`, `IV`, `V`, `vi`, `vii°`) and three selected seventh-chord candidates (`ii7`, `V7`, `viiø7`) relative to the melody-inferred key. The weights remain melody compatibility `0.50`, functional transitions `0.25`, persistence `0.10`, and cadence `0.15`.

**Reference-harmony firewall:** Only melodic events and necessary structural/timing data are passed to the generator. Human-reference chord labels are loaded separately by the evaluator *after* harmonization. The generator does not train on, receive, or optimize against the reference chords. Reference key annotations are likewise used only for the subsequent key audit.

### Running and auditing the corpus experiment

Execute these commands from `Explainable_Melody_Harmonizer/` in a Python environment with the dependencies installed:

```bash
python -m pytest -q
python experiments/run_hooktheory_poc.py
python experiments/audit_hooktheory_poc.py --output results/hooktheory --core emh
```

The experiment requires the HookTheory source archive and selection manifest expected by the local loader. The source dataset is not bundled in this README and should be obtained according to the upstream distribution conditions. Consult the corresponding scripts for any additional path or environment requirements; the commands above assume the project's standard directory layout.

For the **additional post-hoc key audit**, use the separately committed diagnostic script, when present:

```bash
python experiments/audit_hooktheory_keys.py
```

This reads the reference key annotations and the previously generated EMH key results; it must not feed the human-reference key back into the harmonizer. The audit produces `results/hooktheory/key_audit_raw.json` in the current workflow. If using the original frozen Git tag, the later key-audit script may not yet be present and should be checked out from the subsequent diagnostic commit.

The main corpus results and diagnostics are organized under `results/hooktheory/`, including aggregate results and decision-level audit outputs such as `aggregate.json`, `diagnostics.json`, and `diagnostics.md` where present.

### Evaluation protocol

Generated and human harmony are compared on the fixed EMH harmonic-decision grid. The human-reference chord for each segment is selected by **maximum temporal overlap**. This simplifies segments with multiple reference chords: **40 segments** have mixed reference harmony, and **four** have incomplete reference coverage.

Harmonic-function agreement is computed **relative to the key inferred by EMH from melody**, not from independently validated human functional labels. The metrics below use different denominators and should not be interpreted as interchangeable measures of musical quality.

| Measure | Matches / evaluated | Rate |
| --- | ---: | ---: |
| Chord-root agreement | 139 / 439 | 31.66% |
| Exact chord agreement | 90 / 439 | 20.50% |
| Harmonic-function agreement (EMH-inferred key) | 200 / 420 | 47.62% |
| Candidate chord coverage | 236 / 439 | 53.76% |
| Candidate root coverage | 420 / 439 | 95.67% |
| Exact chord agreement, conditional on candidate coverage | 90 / 236 | 38.14% |
| Root agreement on unmixed segments | 125 / 399 | 31.33% |

### Decision-level diagnostics

The 439 evaluated segments are partitioned into three **mutually exclusive** outcomes:

| Outcome | Segments | Share |
| --- | ---: | ---: |
| Exact human-reference chord match | 90 | 20.50% |
| Reference chord absent from the available candidate set | 203 | 46.24% |
| Reference chord available but not selected | 146 | 33.26% |
| **Total** | **439** | **100.00%** |

This separates a **representational constraint** (the reference chord was not selectable under the detected key and frozen vocabulary) from a **selection difference** (the chord was selectable but another path won). The latter does **not** identify which scoring component caused the decision; controlled ablation or counterfactual analysis would be required for causal attribution. Neither category implies that the generated chord is aesthetically incorrect.

### Post-hoc tonal-context audit

A separate audit compares EMH's melody-derived key with the HookTheory reference key annotation. An exact tonic pitch-class and major/minor mode match was observed in **8 of 19 processed excerpts (42.1%)**. The other annotations differ in tonic, mode, or scale type. This comparison is **post-hoc** and does not change the original generation or seven metrics above.

The limited key agreement cautions against interpreting the **47.62% harmonic-function agreement** as an independently validated match to human harmonic intention. Key annotations were not independently verified against the full musical context, and short melodies may support ambiguous or alternative tonal interpretations. Tonal-context differences may interact with both candidate availability and chord selection; they are **not a fourth mutually exclusive segment outcome**.

### Interpretation and future work

The corpus experiment measures correspondence with one human-annotated harmonic reference, **not subjective musical quality**, nor whether a generated chord is the only correct harmonization. It does not include a listening test or a human usability study.

The decision-level audit can help musicians, teachers, and researchers inspect alternative harmonic decisions and formulate targeted experiments. Potential educational or human–AI collaboration benefits remain hypotheses for future human-centered evaluation.

Future controlled studies can vary candidate vocabulary (including additional sevenths, sixths, secondary dominants, and extensions), key inference, harmonic segmentation, and scoring weights **as separately versioned experiments**, while preserving the original v0.12 baseline.

### Corpus-related project files

The corpus workflow extends the original MusicXML-only structure with:

- `hooktheory/` — HookTheory parsing/adaptation and related support code.
- `experiments/run_hooktheory_poc.py` — frozen corpus evaluation runner.
- `experiments/audit_hooktheory_poc.py` — decision-level diagnostics.
- `experiments/audit_hooktheory_keys.py` — later post-hoc tonal-context audit, when committed.
- `results/hooktheory/` — experiment summaries and diagnostic outputs.
- `data/hooktheory/` — local source-data location where configured; source data may be untracked and subject to upstream licensing.

For the publication's reproducibility reference, use the Git tag `emh-v0.12.1-hooktheory` and identify any later diagnostic commit separately.

---

## Status

EMH v0.12 is implemented and operational as a frozen experimental explainable harmonization baseline.

The current system supports the complete reproducible workflow:

```text
MusicXML melody
→ key detection
→ meter-aware segmentation
→ chord candidates
→ explicit scoring
→ global Viterbi-like optimization
→ explainable JSON/CSV results
→ separate post-hoc comparison with human harmony
```

The six experimental MusicXML inputs are included in `examples/`, and the commands required to reproduce each harmonization run are documented above. The HookTheory experiment and its post-hoc diagnostics are described in the dedicated section below.
