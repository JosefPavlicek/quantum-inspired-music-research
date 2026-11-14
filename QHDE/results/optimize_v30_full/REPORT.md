# QHDE v0.30 — offline batch optimization (v0.24 optimizer)

- Source manifest SHA256: `7b5b672006c8b8c7fb686c4fae7aa61259d8ace6eb4225b0d3347962831417c7`
- Completed instances: **400**; distinct landscapes: **389**
- Feasibility counts: {4: 12, 16: 14, 64: 69, 256: 305}
- Random starts per depth: **6**; maxiter: **120**; seed: **42**
- No IBM QPU submitted; exact statevector QAOA, no hardware noise.
- v0.24 objective: minimize expected energy INCLUDING infeasibility penalty; optimize p1/p2/p3 separately, warm-start p>1.
- No classical speedup/quantum advantage claim. Feasible optima from exact enumeration of 256 states.
- Source is HookTheory TRAIN only; internal clean validation is not an external holdout.
- Validation leakage flag and landscape hashes retained; treat repeated musical-source clips as potentially dependent.

| Subset | Records | Distinct landscapes |
|---|---:|---:|
| full (256 feasible) | 305 | 305 |
| restricted (<256 feasible) | 95 | 84 |
| internal train | 305 | 298 |
| clean internal validation | 91 | 91 |

## Mean ideal optimum probability (not hardware)

| Depth | All | Full | Restricted |
|---|---:|---:|---:|
| p=1 | 8.41% | 10.26% | 2.51% |
| p=2 | 16.46% | 20.33% | 4.04% |
| p=3 | 23.12% | 28.45% | 6.01% |
