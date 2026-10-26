# HARMONIX v0.8.0 — Harmonic Vocabulary Audit

This is a **diagnostic-only** extension. It reads HookTheory reference annotations and
compares them with the frozen EMH candidate vocabulary, without changing the EMH
engine, baseline, oracle experiment, or its TEST selection.

From repository root, with HARMONIX virtual environment activated:

```bash
cd HARMONIX
python -m harmonix.vocabulary_audit \
  --selection ../Explainable_Melody_Harmonizer/selection.json \
  --output-prefix results/vocabulary_audit --limit 20
```

Outputs `results/vocabulary_audit.json` and `.csv`. Failures retain stderr in JSON.
The CSV contains one row per EMH segment, including missing/mixed labels.
`out_of_vocabulary` can include valid chord types that EMH does not generate,
chromatic roots, candidate constraints, or pitch-class mismatches. The audit
reports **diagnostic observations, not proof of any single cause**.

Classification is by root-relative pitch-class set; it does not infer voicing,
actual inversion, omitted fifths, functional role, or harmonic quality.
HookTheory `root_position_intervals` are cumulative steps. `relative_pitch_classes`
are deduplicated modulo 12. The worker deliberately uses the **same reference
alignment rule** as v0.7.1, for comparability.

## Scientific firewall

TEST reference is used **only for post-hoc audit**, not to choose interventions,
expand the model, tune thresholds or report a newly optimized TEST result. Any
new vocabulary/selection policy must be developed on a separate DEVELOPMENT set,
then evaluated on a held-out TEST set. Do not treat a diagnostic audit as a
successful intervention experiment.

## Files changed

Only new files inside `HARMONIX/`. No modifications to original or frozen EMH.
