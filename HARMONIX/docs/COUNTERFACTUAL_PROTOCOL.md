# HARMONIX v0.3.0 — Counterfactual Decision Kernel

This release adds an **independent**, deterministic, finite-state dynamic-programming model.
It does not change the pinned EMH baseline or existing knowledge/notation modules.

## Capabilities
- Optimize a complete sequence from local and pairwise transition scores.
- Force one choice at one position and **re-optimize the entire sequence**.
- Enumerate feasible single-position counterfactuals.
- Rank positions by maximum number of changed choices, without using reference harmony.
- Separately evaluate exact-choice agreement with a reference after selection.

## Research limitations
1. This is a **research kernel**, not yet connected to the real EMH candidate and scoring pipeline.
2. Maximum influence is a structural-sensitivity metric, **not evidence of improvement**.
3. The current distance is exact-choice Hamming distance, not a musical function/cadence metric.
4. Forcing a particular chord from a reference would reveal target information; subsequent experiments must explicitly budget and disclose this information.
5. Selecting the best forced alternative using the reference would be data leakage. Selection must be independent of the reference.
6. Dynamic programming here assumes additive first-order transitions. Longer-range musical dependencies require a richer state or another optimizer.
7. No claims about human emotions, musical quality, or composer intent follow from these tests.

## Next milestone
Connect EMH segmentation/candidates/scoring via an adapter **without editing vendor/**.
Then implement reference-blind intervention policy, reference-conditioned response protocol,
random baselines with equal intervention budgets, and held-out song-level evaluation.
