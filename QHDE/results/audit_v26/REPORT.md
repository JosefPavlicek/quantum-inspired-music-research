# QHDE v0.26: offline hardware–ideal gap audit

Job `dbh8j5kdgr2s73ct1100`, backend `ibm_marrakesh`, 12 instances, 48 circuits.

| Model | Hardware (%) | Ideal (%) | Gap (pp) | Ratio of means |
|---|---:|---:|---:|---:|
| uniform | 1.20 | 1.24 | -0.03 | 0.974 |
| p1 | 6.68 | 9.91 | -3.23 | 0.674 |
| p2 | 10.34 | 19.12 | -8.77 | 0.541 |
| p3 | 12.49 | 28.17 | -15.67 | 0.444 |

## Paired hardware comparisons

| Pair | Mean difference (pp) | Positive/negative/tied | Exact sign-flip p | 95% bootstrap CI (pp) |
|---|---:|---:|---:|---:|
| p1_minus_uniform | +5.48 | 12/0/0 | 0.0005 | [3.74, 7.41] |
| p2_minus_p1 | +3.66 | 11/1/0 | 0.0029 | [1.75, 5.73] |
| p3_minus_p2 | +2.15 | 9/2/1 | 0.0205 | [0.63, 3.94] |
| p3_minus_p1 | +5.81 | 11/1/0 | 0.0034 | [2.66, 9.34] |
| p3_minus_uniform | +11.29 | 12/0/0 | 0.0005 | [7.45, 15.62] |

## Caveats

- Paired tests use songs/instances as units, not 1024 shots as independent songs.
- Music cases may share Hamiltonian landscapes; song-level confidence intervals may overstate independent information.
- Per-instance Wilson intervals capture shot uncertainty, not device drift or instance-sampling uncertainty.
- CX/depth here come from v0.23 logical circuits, not backend-transpiled v0.25 circuits.
- Correlation of noise gap with depth is confounded by QAOA layer count and instance-specific effects.
- Global optimum is defined by the modeled corrected-EMH score, not human preference.
- No quantum advantage is claimed; 256 states are trivially classically enumerable.
