# HARMONIX v0.8.1 — Vocabulary diagnostics

This patch **only reads** an existing v0.8.0 `vocabulary_audit.json`.
It does not modify original EMH, frozen EMH, dataset, or harmonizer scores.

From repository root:

```bash
cd HARMONIX
python -m harmonix.vocabulary_diagnostics --input results/vocabulary_audit.json --output results/vocabulary_diagnostics.json
python -m unittest discover -s tests
```

## Scientific interpretation

- `oov_common_quality_count` identifies reference chords whose **qualities are familiar**, but which are not among the generated candidates. It does **not** mean the engine supports every root/quality combination.
- `oov_root_available_count` means *some* candidate has the same root; it does **not** mean the required chord quality exists.
- `oov_pitch_class_available_count` means a candidate has the same pitch-class set regardless of root. It does not establish musical equivalence.
- No new candidate generation is performed. This diagnostic cannot demonstrate how much coverage an expanded vocabulary would recover.
- The report uses reference annotations; keep it outside reference-blind intervention selection and do not tune on held-out TEST.

## Next implementation checkpoint

Inspect the frozen candidate-generation API and the key-detection outputs on development songs. Only then implement an **independent HARMONIX candidate-extension adapter**, with frozen baseline unchanged. Pre-register candidate rules and evaluate on a separate held-out split.
