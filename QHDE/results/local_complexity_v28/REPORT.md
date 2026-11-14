# QHDE v0.28: Local harmonic decision complexity

- Hardware job: `dbh8j5kdgr2s73ct1100`; **12** unique instances; no QPU use.
- Descriptors reconstructed from the exact four unary and three transition score tables in v0.22.
- **Not reference-harmony entropy**: no verified HookTheory alignment to the four segments has been performed.
- Pair coupling removes unary effects by double centering; all scores normalized by 256-state score span.
- Confirmed numerical equality of factorized and full 256-state scores for every instance.

## Correlations (exploratory; FDR over all nonconstant tests)

| Feature | Outcome | Spearman rho | permutation p | FDR q |
|---|---|---:|---:|---:|
| unary_margin_mean | ideal_gain_p3_p2 | 0.722 | 0.013 | 0.262 |
| unary_optimum_in_global | hardware_gain_p3_p2 | 0.667 | 0.025 | 0.262 |
| unary_margin_mean | hardware_noise_gap_p3 | 0.592 | 0.043 | 0.304 |
| near_optimal_fraction | ideal_gain_p3_p2 | -0.481 | 0.114 | 0.477 |
| coupling_rms | hardware_gain_p3_p2 | -0.420 | 0.168 | 0.477 |
| frustration_loss | hardware_gain_p3_p2 | -0.417 | 0.169 | 0.477 |
| unary_optimum_in_global | ideal_gain_p3_p2 | 0.410 | 0.215 | 0.477 |
| unary_margin_mean | hardware_gain_p3_p2 | 0.395 | 0.206 | 0.477 |
| unary_optimum_in_global | hardware_noise_gap_p3 | 0.358 | 0.291 | 0.477 |
| near_optimal_fraction | hardware_noise_gap_p3 | -0.357 | 0.249 | 0.477 |
| coupling_to_unary_ratio | hardware_gain_p3_p2 | -0.347 | 0.257 | 0.477 |
| near_optimal_fraction | hardware_gain_p3_p2 | -0.345 | 0.270 | 0.477 |
| unary_ambiguity_bits | hardware_noise_gap_p3 | 0.336 | 0.295 | 0.477 |
| frustration_loss | ideal_gain_p3_p2 | -0.292 | 0.355 | 0.531 |
| coupling_to_unary_ratio | hardware_noise_gap_p3 | 0.280 | 0.379 | 0.531 |
| unary_ambiguity_bits | hardware_gain_p3_p2 | -0.231 | 0.466 | 0.598 |
| coupling_rms | hardware_noise_gap_p3 | 0.224 | 0.484 | 0.598 |
| frustration_loss | hardware_noise_gap_p3 | -0.174 | 0.575 | 0.671 |
| unary_ambiguity_bits | ideal_gain_p3_p2 | 0.112 | 0.713 | 0.784 |
| coupling_to_unary_ratio | ideal_gain_p3_p2 | 0.105 | 0.746 | 0.784 |
| coupling_rms | ideal_gain_p3_p2 | 0.056 | 0.866 | 0.866 |

## Leave-one-instance-out: hardware gain p3 minus p2

| Model | MAE (percentage points) | Mean-only baseline (pp) |
|---|---:|---:|
| local_margins | 2.553 | 2.504 |
| interaction | 2.902 | 2.504 |
| combined | 3.019 | 2.504 |

## Interpretation and limitations

- n=12; stratum-based nonrandom selection; correlations are descriptive, not causal.
- 1024 shots per circuit and a single eight-qubit hardware run: winner labels are noisy.
- All descriptors arise from the same EMH objective that defines the optimum: potential mathematical coupling, not independent human-validated music complexity.
- We do not claim quantum advantage; 256 states can be enumerated classically.
- Future genuinely musical local descriptors require independently verified annotation-to-segment temporal alignment.
