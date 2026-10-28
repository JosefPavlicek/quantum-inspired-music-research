# QHDE v0.15 — Offline landscape exploration

**Not yet musical-complexity research.** These descriptors summarize 16 model-defined scores, and are deliberately separated from independently measured full-song harmonic properties.

| Record | Tied optima | Distinct scores | Score SD | p2–p1 (pp) | Ideal p2–p1 (pp) |
|---|---:|---:|---:|---:|---:|
| LAgQGkwEoyO | 1 | 14 | 0.1469 | +5.96 | +8.25 |
| bWgMvrVkxlX | 9 | 4 | 0.0600 | -4.49 | +0.04 |
| DpgvlyPBoad | 3 | 4 | 0.0616 | +21.48 | +26.57 |
| nZgWXMVQxry | 2 | 6 | 0.0754 | +7.91 | +8.22 |
| RPxeyBjaxb_ | 1 | 8 | 0.0863 | -3.42 | +2.35 |

## Exploratory associations (n=5; not inferential)

- optimum_count: r = -0.323
- distinct_scores: r = -0.150
- range_score: r = -0.197
- best_second_distinct_gap: r = +0.640
- score_sd: r = -0.088
- shifted_score_entropy_bits: r = -0.891

## Next scientific stage

Use full HookTheory songs with verified chord annotations to compute independent musical features (transition entropy, harmonic vocabulary, functional diversity, non-diatonic rate, repetition); compare with circuit-depth response while controlling for optimization-landscape complexity. Do not infer full-song complexity from this two-segment score export.

## Limitations

- These are optimization-score landscape descriptors, NOT independently measured musical-complexity features.
- Five related TRAIN cases are insufficient for inferential correlations or predictive claims.
- Model-selected 4x4 subset; original 10x10 task not solved by QAOA.
- Ideal p1/p2 differ before hardware noise: depth effect is not attributable to noise alone.
- Complexity analysis of full-song human chord sequences requires original HookTheory records and reliable parsing.
- Bit-to-basis mapping must be independently audited before final publication.
