# QHDE v0.32 — harmonic-dependency ablation and practical routing audit

- Instances: **400**; landscapes: **389**.
- Full score factorization numerically checked on feasible states for every instance.
- All ablations retain exactly the same feasibility mask; restricted cases require exact enumeration.
- Unary-only decision selects feasible maximizer of sum of unary scores; compare its TRUE original EMH score against joint optimum.
- Shuffled-transition controls permute each 4x4 transition matrix (same multiset of 16 values), then optimize under the original feasibility mask and evaluate the resulting choice on ORIGINAL EMH.
- Shuffling is a negative control, not a valid musical alternative or a matched Hamiltonian complexity control.
- Full-feasible cases have an exact O(3*4^2) dynamic-programming solver; validated against exhaustive enumeration.
- Routing by actual regret is an ORACLE analysis and cannot be deployed without computing the joint optimum; DP itself is the practical default.
- NOT a QAOA run: existing v0.30 QAOA results remain a separate optimization study.

| Subset | n | Mean loss unary vs joint (normalized) | Mean benefit correct over shuffled links (normalized) |
|---|---:|---:|---:|
| all | 400 | 0.0405 | 0.0387 |
| fully feasible | 305 | 0.0417 | 0.0262 |
| restricted | 95 | 0.0365 | 0.0789 |
| training full feasible | 235 | 0.0405 | 0.0269 |
| validation full feasible | 70 | 0.0459 | 0.0238 |

## Practical decision

- Diagnostic cutoff: 0.020 of original feasible score span, **fixed before analysis**.
- The scientifically valid deployable baseline is dynamic programming for fully feasible four-chord chains, not QAOA.
- For masked tasks the non-factorizing feasibility constraints invalidate simple DP; check mask structure before considering an efficient constrained solver.
- Next test: fit a genuinely cheap router from unary-only statistics and compare validation cost/quality against always-DP and always-unary.
- Distinct landscape hashes do not guarantee independent songs. HookTheory TRAIN-only validation is not external validation.
- Do not interpret the shuffled-transition comparison as causal evidence of musical meaning without independent human evaluation.
