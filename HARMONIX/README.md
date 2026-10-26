# HARMONIX
## Author: Josef Pavlíček ORCID: https://orcid.org/0000-0002-3959-5406

**Human-Aware Reasoning for Musical Optimization and eXplainability**

HARMONIX is an experimental, explainable **melody-to-harmony research system**. It studies how explicit structural rules change generated chord decisions and their agreement with human-annotated harmony. It is a research platform, **not** an AI-music-authenticity detector, a commercial arranger, or a system that infers a composer's intentions.

## What it currently does

1. Reads melodic material from a HookTheory corpus record, withholding its annotated chords during generation.
2. Estimates a key, segments the melody and constructs a corrected chord-candidate vocabulary.
3. Generates a chord path using frozen Explainable Melody Harmonizer (EMH) scoring and optimization, or applies additional explicit structural rewards.
4. Finds nonadjacent recurring melodic signatures (relative pitch-class contour and normalized durations). **These signatures are transposition-invariant**; matching signatures do not necessarily indicate the same absolute-pitch motif.
5. Compares generated chords with the withheld HookTheory annotations **after generation**, using six reference-agreement metrics.
6. Runs paired four-arm corpus experiments, audits failures, and computes work-proxy-clustered bootstrap intervals.

The structural optimizer is a **deterministic iterative approximation**, not a globally exact optimizer. It uses four iterations in the reported experiments. The frozen EMH source remains untouched.

## Research variants

All four variants share the **same corrected chord candidates** and underlying EMH scoring. The numbers below are structural reward weights, not probabilities.

| Benchmark arm | Short name | Motif repetition weight | Function-transition weight |
| --- | --- | ---: | ---: |
| `corrected` | corrected EMH | 0 | 0 |
| `repetition` | HARMONIX-R | 0.12 | 0 |
| `function` | HARMONIX-F | 0 | 0.06 |
| `combined` | HARMONIX-RF | 0.12 | 0.06 |

The benchmark is **not** a comparison against an entirely different model architecture for each arm. `corrected` is the reference-blind, corrected-vocabulary baseline; it is distinct from running the original EMH through the `baseline` CLI command.

## Repository layout and isolation

- `harmonix/`: candidate generation, structural optimization, benchmarks, diagnostics and analysis.
- `vendor/emh_baseline/`: frozen EMH source snapshot; **do not edit**.
- `vendor/emh_sha256.json`: source integrity manifest checked by the baseline adapter and benchmark initialization.
- `fixtures/`: example MusicXML melody for the original baseline adapter.
- `tests/`: automated regression tests.
- `results/`: locally generated output; large HookTheory archives and experimental results are not supplied by this README.
- The sibling `Explainable_Melody_Harmonizer/` repository directory, if present, is not modified by HARMONIX.

## Requirements and installation

Run from the `HARMONIX/` directory with Python **3.11 or newer**. The benchmark additionally needs the existing EMH/HookTheory integration and the SheetSage HookTheory archive; check the local dataset configuration if automatic archive discovery fails.

```bash
cd HARMONIX
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m harmonix.cli verify-baseline
python -m pytest -q tests
```

Run the regression tests against your current checkout. Passing unit tests verifies local code behavior; it does **not** reproduce the full third-party-corpus experiment.

## Third-party dataset: access, attribution and licensing

The large-scale experiment uses **HookTheory chord/melody annotations distributed in the SheetSage HookTheory dataset/archive**. The corpus and its annotations are third-party material: **they are not authored by HARMONIX, not included in this repository, and are not automatically redistributable under the HARMONIX source-code license**. Researchers must obtain the data from the original provider/distributor, following its current access, permission, citation and licensing terms. Consult the [SheetSage project](https://github.com/chrisdonahue/sheetsage) and the [Hooktheory website](https://www.hooktheory.com/) to identify the relevant dataset release and request or arrange access with the appropriate rights holder. These links are starting points, not a claim that a public download or redistribution permission exists.

After authorized acquisition, store the dataset **outside Git** and pass the local path via `--archive /path/to/Hooktheory.json.gz` where supported. Never commit the raw archive, extracted records, or human annotations without permission. For exact reproduction, retain the same archive/version and the original frozen TRAIN/VALID manifests; regenerating splits may change the evaluation population. If the original manifests are unavailable, results from newly generated manifests are a **new experiment**, not an exact replication of the reported numbers.

The included MusicXML fixture is a *software smoke test*, **not** a substitute for the third-party evaluation corpus.

## Example A — original EMH baseline on MusicXML

```bash
python -m harmonix.cli baseline \
  --input fixtures/LaBamba_melody.musicxml \
  --output results/baseline
```

This command invokes the **original frozen EMH** via a separate process and writes its native outputs under `results/baseline/`. It does **not** activate HARMONIX-R, -F or -RF. The four-arm structural experiment currently uses the corpus benchmark interface below, rather than a public MusicXML-to-RF CLI.

## Example B — audit corpus and prepare manifests

Provide the corpus explicitly if it is not discoverable by the project's existing data loader:

```bash
python -m harmonix.corpus_audit \
  --archive /path/to/Hooktheory.json.gz \
  --output results/corpus_audit.json \
  --manifest-dir results/corpus_manifests
```

The audit writes `train_full.json`, `valid_full.json`, and `test_full.json` manifests, each containing record IDs and artist/song identifiers. **Do not regenerate a new split and treat it as the previously reported experiment**: for strict reproduction, reuse the original frozen manifests and dataset version.

## Example C — quick four-arm structural experiment

A ten-record smoke test (the `--limit` default is 50; `--limit 0` processes the entire manifest):

```bash
python -m harmonix.structural_benchmark \
  --manifest results/corpus_manifests/valid_full.json \
  --archive /path/to/Hooktheory.json.gz \
  --limit 10 \
  --output results/demo_valid.jsonl \
  --summary results/demo_valid_summary.json
```

Outputs: one JSON object per record in `.jsonl`, an associated `.settings.json` sidecar used for safe resume, and a JSON summary. Use a **new output filename** when changing inputs or parameters. The benchmark uses the four frozen weights above and defaults to four optimization iterations.

## Example D — full VALID benchmark and clustered RQ analysis

```bash
python -m harmonix.structural_benchmark \
  --manifest results/corpus_manifests/valid_full.json \
  --archive /path/to/Hooktheory.json.gz \
  --limit 0 \
  --output results/structural_valid_all.jsonl \
  --summary results/structural_valid_all_summary.json

python -m harmonix.rq_final_analysis \
  --manifest results/corpus_manifests/valid_full.json \
  --results results/structural_valid_all.jsonl \
  --output results/rq_valid_final.json \
  --bootstrap 1000 --seed 2027
```

For the final **v0.19 transposition-aware** experiment, run the diagnostic workflow. It evaluates the same four configurations and adds post-generation contextual analysis; it does not alter candidate generation, scoring, optimization, or weights:

```bash
python -m harmonix.structural_reference_diagnostics \
  --manifest results/corpus_manifests/valid_full.json \
  --archive /path/to/Hooktheory.json.gz \
  --limit 0 \
  --output results/structural_reference_valid_v019.jsonl \
  --summary results/structural_reference_valid_v019_summary.json
python -m harmonix.rq_final_analysis \
  --manifest results/corpus_manifests/valid_full.json \
  --results results/structural_reference_valid_v019.jsonl \
  --output results/rq_valid_v019.json \
  --bootstrap 1000 --seed 2027
```

Repeat for TRAIN, using `train_full.json` and corresponding distinct `train_v019` output names. See `EXPERIMENT_V019.md` for the exact TRAIN commands and diagnostic definitions. The diagnostic module requires the v0.19 patch; check that it exists before running. The output paths shown here are **local generated paths**, not a promise that those files are checked into Git. Avoid overwriting earlier experimental runs; preserve the `.settings.json` sidecars and record the source commit.

### Where to find results

- `results/structural_reference_{train,valid}_v019.jsonl`: per-record diagnostic output, if generated with these names.
- `results/structural_reference_{train,valid}_v019_summary.json`: run-level summaries and failure counts.
- `results/rq_{train,valid}_v019.json`: paired baseline-relative estimates, bootstrap confidence intervals and `transposition_pair_level` strata.
- `results/corpus_manifests/{train,valid}_full.json`: split manifests required to reproduce the experiment.
- `EXPERIMENT_V019.md`: technical description of the diagnostic patch and its limitations.

Result files are **not necessarily committed or distributable**. Published summary statistics can be shared separately when permitted; record-level outputs may contain derived third-party information and require a licensing review.

## How to interpret the metrics

| JSON metric | Meaning |
| --- | --- |
| `chord_agreement` | Agreement of generated and annotated chord identities at evaluated segments. |
| `root_agreement` | Agreement of chord roots. |
| `function_agreement` | Agreement of encoded harmonic-function labels. |
| `exact_chord_transition` | Fraction of adjacent evaluable segment pairs where **both** generated chords match the annotations. |
| `repeated_pair_both_correct` | Fraction of evaluable repeated-motif pairs where **both** generated chords match the annotations. |
| `repeated_pair_reference_relation` | Agreement between generated and annotated **same-root vs different-root** relationships across repeated-motif pairs; not a general structural-consistency score. |
| `generated_matches_reference_interval` | In v0.19 motif-pair diagnostics, whether the **generated chord-root interval** equals the **annotated chord-root interval**, modulo 12. This is the primary transposition-aware comparison. |

The summary JSON contains **unweighted per-record means**. `rq_final_analysis` reports paired differences in **percentage points** and 95% work-proxy-cluster bootstrap intervals (artist/song groups), with 1,000 resamples by default. Those intervals are exploratory, not multiplicity-adjusted, and are not proof of causal or artistic superiority.

## Research questions and observed results (v0.19)

The engineering focus is **how explicit domain constraints affect optimization-based decision systems**. Musical harmonization provides a structured experimental testbed, not a claim that the findings already generalize to other information systems.

- **RQ1:** Do explicit structural rules improve correspondence with observable patterns in human-created reference decisions? **Conditionally**: improvements occur in stable contexts, while some transformations deteriorate.
- **RQ2:** What are the individual and combined effects of repetition (R) and harmonic-function (F) constraints? R drives the largest gains and losses; F has smaller context-dependent effects; combining R and F is not universally synergistic.
- **RQ3:** How stable are these effects across partitions and contexts? TRAIN and VALID show the same direction of effects across all four analyzed contexts; this does not establish external generalizability or song-by-song uniformity.

### Experiment coverage

| Quantity | TRAIN | VALID |
| --- | ---: | ---: |
| Records attempted | 17,923 | 1,822 |
| Successfully processed | 17,911 | 1,821 |
| Failed | 12 | 1 |
| Work-proxy clusters | 10,623 | 1,111 |
| Evaluated motif pairs | 131,117 | 12,517 |

The causes of failed records must be checked in detailed logs; the aggregated counts alone do not establish their causes or prove that exclusions have no effect.

### Context-specific interval agreement

The outcome is `generated_matches_reference_interval`. All entries below are **percentage-point differences from Corrected EMH** (positive = higher reference interval agreement). `n` counts evaluated motif pairs, not independent songs.

| Context | TRAIN n | TRAIN R | TRAIN F | TRAIN RF | VALID n | VALID R | VALID F | VALID RF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| No transposition; same reference root | 60,944 | +4.77 | +3.87 | +5.08 | 5,922 | +4.91 | +3.88 | +5.00 |
| No transposition; changed reference root | 27,673 | -1.45 | -0.73 | -1.52 | 2,639 | -0.95 | -0.45 | -0.99 |
| Transposed; reference root tracks melody | 10,958 | -8.08 | -1.59 | -8.80 | 1,064 | -8.93 | -2.44 | -8.93 |
| Transposed; reference root does not track melody | 31,542 | +3.95 | +0.74 | +4.13 | 2,892 | +3.46 | +1.11 | +4.18 |

For the **transposed/reference-tracks-melody** stratum, absolute agreement is:

| Configuration | TRAIN | VALID |
| --- | ---: | ---: |
| Corrected EMH | **27.68%** | **29.23%** |
| R | 19.60% | 20.30% |
| F | 26.09% | 26.79% |
| RF | 18.88% | 20.30% |

RF relative to Corrected EMH: **TRAIN -8.80 pp** (95% work-proxy-cluster bootstrap CI [-9.71, -7.97]); **VALID -8.93 pp** (CI [-11.68, -6.45]). Conversely, RF improves stable untransposed/same-root agreement by **+5.08 pp** on TRAIN and **+5.00 pp** on VALID.

Overall exact chord agreement changes only slightly: RF vs Corrected EMH is **+0.059 pp** on TRAIN (95% CI [+0.006, +0.114]) and **+0.068 pp** on VALID (95% CI [-0.117, +0.229]). Thus, the main finding is a **context-specific trade-off**, not a major increase in global exact chord accuracy.

### Diagnostic definitions and interpretation

The repeated-motif matcher uses a transposition-invariant relative melodic signature. For each matched pair, the diagnostic approximates melodic transposition by the difference between the first sounding pitch classes. Reference and generated chord-root shifts are compared modulo 12. The four categories distinguish zero/nonzero melodic shift and whether the *reference* root shift matches that melodic shift. This is an **evaluation-only classification**: the generator does **not** observe the reference chords when making predictions. `repeated_pair_reference_relation` is a coarser binary same/different-root measure and must not be conflated with exact interval agreement.

**Limitations:** the source contains human chord annotations, not unique correct harmonies or evidence of composer intention; a single pitch-class shift is not full phrase/transposition analysis; octave, enharmonic spelling and expressive context are omitted. Pairs are correlated, so the reported uncertainty uses **1,000 work-proxy-cluster bootstrap resamples**, seed **2027**. Artist/song identifiers are work proxies rather than verified unique works. TRAIN is exploratory, VALID is not a pristine confirmatory holdout, and the exploratory intervals are not adjusted for multiple comparisons. No claim is made that a future adaptive constraint selector has been implemented or validated.

### Systems-engineering implications

Static structural constraints can improve stable relationships while hindering context-sensitive transformations. A future design may include **context detection and constraint applicability/weighting**, but this is an **architectural hypothesis**, not an implemented HARMONIX v0.19 feature. All four tested arms use the same underlying search mechanism; these results do not establish that Viterbi is superior to other optimizers.

## Reproducibility and provenance

The original baseline snapshot derives from the researcher-provided `EMH_CAiSE_2027.zip`; file hashes are recorded in `vendor/emh_sha256.json`. The v0.19 diagnostics add reporting only, not new scoring weights. For a paper, archive the precise source commit, manifest files, dataset identifier/version, result JSONLs and `.settings.json` sidecars, summary JSONs, bootstrap settings, failure counts and analysis scripts. Avoid committing copyrighted or bulky corpus data without permission.

The software is a longer-term research platform, independent of any single conference submission. See the existing `INSTALL_*` and `UPGRADE_*` notes for historical migration details.
