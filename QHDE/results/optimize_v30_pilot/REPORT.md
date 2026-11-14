# QHDE v0.30 — offline batch optimization (v0.24 optimizer)

- Source manifest SHA256: `7b5b672006c8b8c7fb686c4fae7aa61259d8ace6eb4225b0d3347962831417c7`
- Completed instances: **5**; distinct landscapes: **5**
- Feasibility counts: {64: 1, 256: 4}
- Random starts per depth: **2**; maxiter: **35**; seed: **42**
- No IBM QPU submitted; exact statevector QAOA, no hardware noise.
- v0.24 objective: minimize expected energy INCLUDING infeasibility penalty; optimize p1/p2/p3 separately, warm-start p>1.
- No classical speedup/quantum advantage claim. Feasible optima from exact enumeration of 256 states.
- Source is HookTheory TRAIN only; internal clean validation is not an external holdout.
- Validation leakage flag and landscape hashes retained; treat repeated musical-source clips as potentially dependent.

| Subset | Records | Distinct landscapes |
|---|---:|---:|
| full (256 feasible) | 4 | 4 |
| restricted (<256 feasible) | 1 | 1 |
| internal train | 2 | 2 |
| clean internal validation | 3 | 3 |

## Mean ideal optimum probability (not hardware)

| Depth | All | Full | Restricted |
|---|---:|---:|---:|
| p=1 | 7.12% | 8.59% | 1.23% |
| p=2 | 13.83% | 16.99% | 1.20% |
| p=3 | 16.55% | 19.99% | 2.77% |
