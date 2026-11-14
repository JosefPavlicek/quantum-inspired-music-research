# QHDE v0.29 — Expanded four-segment benchmark

- Audited TRAIN clips in original manifest: **17923**
- Preselected music-only candidates: **20**
- Valid EMH four-segment problems: **20**
- Distinct affine-normalized landscapes: **20**
- Internal training instances: **9**
- Leak-safe internal validation instances: **11**
- **No hardware experiment executed; no quantum advantage demonstrated.**

## Interpretation

- Each instance contains 4 consecutive melody segments, 4 fixed candidates per segment, 256 possible states.
- All candidates and harmonic scores come from corrected HARMONIX EMH; human harmony is not used for scoring.
- The TRAIN-only internal validation is not equivalent to an independent TEST corpus.
- Duplicate normalized landscapes must be grouped; music clips need not be independent songs.
- Generated tasks are a dataset, NOT optimized QAOA solutions. Use later offline simulation with prespecified budget.
- Full-song reference entropy remains a proxy; temporal note/harmony alignment requires a separate audit.
