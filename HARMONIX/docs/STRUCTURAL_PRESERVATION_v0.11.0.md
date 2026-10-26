# HARMONIX v0.11.0 — Reference-blind structural intervention evaluation

Research question: Can explicit structural modeling of harmonic decision-making improve preservation of observable composer-derived harmonic patterns when harmonizing from melody alone?

**This is not a claim to infer psychological intentions or emotions.**

The frozen EMH graph and its reference-blind `rank_positions()` are reused unchanged. One position is selected by structural rank before consulting human reference labels. The oracle reveals one chord only at that position. If no clean/in-vocabulary reference exists, the query yields no intervention; the selector is **not** allowed to skip to another position. Uniform-random expectation is computed exhaustively over *all* segment positions, with identical no-op handling. This fixes the coverage-conditioned selection bias of the earlier exploratory HookTheory experiment.

Three descriptive metrics:

1. Exact chord agreement at clean, in-vocabulary reference positions.
2. Exact ordered adjacent chord-pair agreement where both positions have clean, in-vocabulary labels.
3. Repetition consistency: when the human reference repeats the same chord at two covered positions, does the generated output repeat a chord? This metric **does not require the generated chord to be correct** and is not independent of other metrics.

Missing/mixed/OOV reference positions remain in the **query selection universe** and can yield no-op. They are excluded only from metrics requiring labels, so coverage limitations must be reported. The fixed vocabulary cannot test human patterns outside its representable space.

Run from `HARMONIX/`:

```bash
python -m pytest tests/ -q
python -m harmonix.structural_preservation --selection ../Explainable_Melody_Harmonizer/selection.json --limit 20 --allow-exploratory-test --output results/structural_preservation_exploratory.json
```

The existing TEST split has been examined repeatedly; the results are **exploratory only**. For CAiSE confirmatory claims, freeze this protocol before using a new untouched holdout. Do not choose model settings using held-out results. Further work: multi-position budgets, transition-pattern analysis at longer lags, and ablation of structural ranking (these are not implemented here).
