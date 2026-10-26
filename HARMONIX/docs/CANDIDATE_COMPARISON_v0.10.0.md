# HARMONIX v0.10.0 — controlled candidate comparison

This patch introduces **three full Viterbi/EMH scoring runs per song** with identical melody, inferred key, segmentation, and scoring weights. Only the candidate vocabulary changes:

1. `baseline`: exact frozen EMH generator and optimizer.
2. `corrected`: independent v0.9.0 knowledge candidate generator with corrected dominant seventh and harmonic-minor V/V7.
3. `extended`: corrected plus additional seventh chords and secondary dominants.

All variants use the **frozen EMH scoring and optimizer**. This is a controlled *candidate-vocabulary* comparison, not a controlled comparison of individual rules within the expanded vocabulary. The extended candidates' generic `dominant` functional label is a simplification; it does not encode tonicization or target-resolution rewards.

## Installation

Unzip at the repository root. Existing source files are not overwritten. No changes to original EMH or frozen vendor.

From `HARMONIX/`:

```bash
python -m pytest tests/ -q
python -m harmonix.candidate_comparison \
  --selection ../Explainable_Melody_Harmonizer/selection.json \
  --limit 20 \
  --allow-exploratory-test \
  --output results/candidate_comparison_exploratory.json
```

**Why the flag?** The original `selection.json` refers to TEST examples already examined during HARMONIX development. Reusing them is permitted **only for exploratory diagnostics**. Do not claim unbiased confirmation on these songs. For a genuine prospective evaluation, freeze all model rules and use a fresh, untouched holdout. For development, create a separate `DEV` manifest from the corpus DEV split; the command checks the record split.

## Metrics

- `clean`: segments containing exactly one reference chord spanning the entire decision interval.
- `covered`: clean segments whose reference chord matches **root AND pitch-class set** of at least one candidate.
- `selected`: clean segments where the selected chord matches reference root and pitch-class set.
- `coverage_rate_clean` and `selection_rate_clean` use the **same clean-segment denominator** across all variants for each evaluated song.
- Failed songs are listed explicitly. If any variant fails, the song is excluded from **all** three aggregate variants, avoiding differing denominators.
- A chord with the same pitch-class set but a different root is **not** an exact match. Neither matching metric measures musical quality, human intent, voicing, or inversion.

## Reproducibility and interpretation

- Reference harmony is loaded only **after all three paths have been generated**.
- No oracle forcing, tuning, or reference-aware selection is performed.
- The frozen baseline is verified before running; no original code is changed.
- The global search space changes with the candidate vocabulary. Even a higher coverage rate need not imply higher selected agreement.
- The original EMH V7 issue remains present in the baseline on purpose.
- Compound-meter adapter failures remain reported as exclusions; they are not silently patched.
- Future work: isolate key-inference effects, measure selection trade-offs, compare intervention policies on a fresh split, and perform expert listening evaluation.
