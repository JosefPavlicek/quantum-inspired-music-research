# QHDE v0.27 — music, interaction structure, QAOA depth

- IBM job: `dbh8j5kdgr2s73ct1100`; local 8-qubit instances: **12**
- Independent affine-normalized energy landscapes: **12**
- Full-song harmonic entropy is a **proxy**, NOT a local four-segment measurement.
- No new QPU time used.

## Repeated landscapes


## Exploratory rank correlations (sorted by absolute rho)

| Predictor | Outcome | Dataset | n | Spearman rho | permutation p | FDR q |
|---|---|---|---:|---:|---:|---:|
| landscape_gap | noise_gap_p3 | all_songs | 12 | 0.776 | 0.004 | 0.067 |
| landscape_gap | noise_gap_p3 | unique_landscapes | 12 | 0.776 | 0.004 | 0.067 |
| conditional_transition_entropy_bits | benefit_p3_vs_p2 | all_songs | 12 | -0.596 | 0.045 | 0.363 |
| conditional_transition_entropy_bits | benefit_p3_vs_p2 | unique_landscapes | 12 | -0.596 | 0.045 | 0.363 |
| repeated_bigram_rate | noise_gap_p3 | all_songs | 12 | -0.466 | 0.127 | 0.588 |
| repeated_bigram_rate | noise_gap_p3 | unique_landscapes | 12 | -0.466 | 0.127 | 0.588 |
| chord_entropy_bits | benefit_p3_vs_p2 | all_songs | 12 | -0.425 | 0.170 | 0.588 |
| chord_entropy_bits | benefit_p3_vs_p2 | unique_landscapes | 12 | -0.425 | 0.170 | 0.588 |
| pair_variance_share | benefit_p3_vs_p2 | all_songs | 12 | -0.378 | 0.221 | 0.588 |
| pair_variance_share | benefit_p3_vs_p2 | unique_landscapes | 12 | -0.378 | 0.221 | 0.588 |
| z_terms | benefit_p3_vs_p2 | all_songs | 12 | 0.369 | 0.238 | 0.588 |
| z_terms | benefit_p3_vs_p2 | unique_landscapes | 12 | 0.369 | 0.238 | 0.588 |
| chord_entropy_bits | noise_gap_p3 | all_songs | 12 | 0.354 | 0.257 | 0.588 |
| chord_entropy_bits | noise_gap_p3 | unique_landscapes | 12 | 0.354 | 0.257 | 0.588 |
| pair_variance_share | noise_gap_p3 | all_songs | 12 | 0.287 | 0.366 | 0.692 |
| pair_variance_share | noise_gap_p3 | unique_landscapes | 12 | 0.287 | 0.366 | 0.692 |
| landscape_std | noise_gap_p3 | all_songs | 12 | -0.273 | 0.389 | 0.692 |
| landscape_std | noise_gap_p3 | unique_landscapes | 12 | -0.273 | 0.389 | 0.692 |
| cx_p3 | benefit_p3_vs_p2 | all_songs | 12 | 0.237 | 0.451 | 0.722 |
| cx_p3 | benefit_p3_vs_p2 | unique_landscapes | 12 | 0.237 | 0.451 | 0.722 |
| z_terms | noise_gap_p3 | all_songs | 12 | 0.200 | 0.532 | 0.725 |
| z_terms | noise_gap_p3 | unique_landscapes | 12 | 0.200 | 0.532 | 0.725 |
| repeated_bigram_rate | benefit_p3_vs_p2 | all_songs | 12 | 0.189 | 0.550 | 0.725 |
| repeated_bigram_rate | benefit_p3_vs_p2 | unique_landscapes | 12 | 0.189 | 0.550 | 0.725 |
| landscape_gap | benefit_p3_vs_p2 | all_songs | 12 | 0.172 | 0.589 | 0.725 |
| landscape_gap | benefit_p3_vs_p2 | unique_landscapes | 12 | 0.172 | 0.589 | 0.725 |
| cx_p3 | noise_gap_p3 | all_songs | 12 | 0.101 | 0.756 | 0.864 |
| cx_p3 | noise_gap_p3 | unique_landscapes | 12 | 0.101 | 0.756 | 0.864 |
| landscape_std | benefit_p3_vs_p2 | all_songs | 12 | 0.067 | 0.841 | 0.897 |
| landscape_std | benefit_p3_vs_p2 | unique_landscapes | 12 | 0.067 | 0.841 | 0.897 |
| conditional_transition_entropy_bits | noise_gap_p3 | all_songs | 12 | 0.035 | 0.919 | 0.919 |
| conditional_transition_entropy_bits | noise_gap_p3 | unique_landscapes | 12 | 0.035 | 0.919 | 0.919 |

## Leave-one-out prediction vs mean-only baseline

| Dataset | Predictors | MAE (pp) | Baseline MAE (pp) | Predictive R² |
|---|---|---:|---:|---:|
| all_songs | chord_entropy_bits, conditional_transition_entropy_bits, repeated_bigram_rate | 2.541 | 2.504 | 0.106 |
| all_songs | landscape_std, landscape_gap, pair_variance_share | 2.514 | 2.504 | 0.029 |
| unique_landscapes | chord_entropy_bits, conditional_transition_entropy_bits, repeated_bigram_rate | 2.541 | 2.504 | 0.106 |
| unique_landscapes | landscape_std, landscape_gap, pair_variance_share | 2.514 | 2.504 | 0.029 |

## Limitations

- Music features are FULL-SONG HookTheory features, not four-segment-local metrics; selection is stratified on these features; duplicate landscapes may be dependent; multiple testing and small n make inference exploratory; postselected best depth is noisy with 1024 shots; no quantum advantage.
- Duplicate groups are exact only up to the declared 1e-9 tolerance on normalized 256-state energies.
- This assesses predictive association, NOT causality or a validated depth recommendation.
- The 4-segment-local music descriptors require a separate, prespecified extraction protocol.
