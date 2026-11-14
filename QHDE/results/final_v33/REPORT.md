# QHDE v0.33 — FINAL fixed-question analysis

## Locked research question

How do musical complexity and harmonic decision dependencies influence QAOA effectiveness and useful circuit depth?

## Scope and data limitations

- 400 offline tasks; internal validation within HookTheory TRAIN; not independent external music corpus.
- Music entropy and repetition refer to full songs, **not locally aligned four-chord windows**.
- Optimized ideal-state QAOA probabilities reflect fixed parameter-search budget (6 starts, 120 maxiter).
- Local interaction metrics are derived from corrected EMH scoring tables. They quantify model coupling, not independently validated human musical meaning.
- Predictions are ideal/noiseless only. No per-instance IBM outcomes are supplied in this input; hardware results must be treated separately.
- Distinct landscapes do not guarantee distinct independent songs. Bootstrap intervals are instance-level, not independent-song-level.
- The energy gap, feasible-state count and number of optima require knowledge of the full score landscape; models using them are diagnostic, not a cheap deployable depth router.
- Optimizer-score optimum is a model optimum, not independently established perceptual quality or quantum advantage.

## Sample construction

- Split counts: `{'validation_clean': 91, 'train_unique': 298, 'validation_excluded': 4, 'train_duplicate_excluded': 7}`

## Ideal optimization outcomes

| Split | n | Mean gain p2−p1 (pp) | Mean gain p3−p2 (pp) | p3>p2 |
|---|---:|---:|---:|---:|
| train_unique | 298 | 8.442 | 7.025 | 268 |
| validation_clean | 91 | 7.231 | 5.490 | 83 |

## Prediction of ideal p3−p2 gain (validation)

Fixed Ridge(alpha=10), standardized predictors, trained on unique training landscapes only.

| Features | MAE (pp) | Improvement over train-mean (pp) | Instance bootstrap 95% CI (pp) |
|---|---:|---:|---:|
| mean | 4.477 | +0.000 | [+0.000, +0.000] |
| music | 4.585 | -0.107 | [-0.294, +0.076] |
| optimization | 3.926 | +0.551 | [-0.113, +1.206] |
| optimization_plus_music | 3.907 | +0.570 | [-0.086, +1.221] |
| optimization_plus_local | 3.754 | +0.723 | [+0.027, +1.425] |
| all | 3.784 | +0.693 | [-0.006, +1.396] |

## Incremental predictive value (paired validation)

| Comparison | Improvement in MAE (pp) | Instance bootstrap 95% CI |
|---|---:|---:|
| local_over_optimization | +0.172 | [-0.204, +0.530] |
| music_over_optimization | +0.019 | [-0.089, +0.125] |
| music_over_optimization_plus_local | -0.030 | [-0.136, +0.078] |

## Hardware benchmark (separate uploaded IBM summary)

- IBM Marrakesh, job dbhmj3c2d77s739d1v00; 24 selected tasks, 4096 shots per model.
- Uniform 0.76%, p1 7.76%, p2 12.65%, p3 15.17% mean optimal-state probability.
- Mean hardware gain p3−p2 = 2.53 percentage points; 22 positive and 2 negative tasks.
- Hardware–ideal gap rises from 2.72 pp (p1) to 8.02 pp (p2) and 14.53 pp (p3).
- Whole-song transition entropy vs hardware p3−p2 gain: Spearman rho=0.131, uncorrected p=0.542 (exploratory).
- **This analysis does not fit hardware-depth predictors** without per-instance paired IBM observations.

## Fixed conclusion

Increasing QAOA depth improves average model-optimum probability for these tasks; real hardware noise substantially erodes these gains. Whether local harmonic decision interactions explain *additional* gains beyond generic optimization structure is evaluated using the holdout models above; negative outcomes must remain negative. No demonstrated quantum advantage against classical dynamic programming.
