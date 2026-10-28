# QHDE research summary — 2026-10-28

## Purpose

Study whether quantum interference can sample high-scoring neighboring harmonic decisions, using explicit musical rules from corrected candidate generation in HARMONIX and unchanged EMH scoring. The published EMH remains frozen; HookTheory melody-only inputs are reference-blind. No human preference, quantum speedup or advantage is yet established.

## Milestones (initial five TRAIN records)

- v0.1: 2-qubit Grover interference demonstration, ideal simulation.
- v0.4: exported 100 candidate-pair scores for each of five HookTheory TRAIN records.
- v0.5: 7-qubit QAOA ideal simulator. Optimum probabilities for p=2: 2.21%, 11.64%, 4.30%, 2.56%, 3.46% (ties vary by record).
- v0.6: Qiskit / NumPy circuit equivalence checks passed.
- v0.7: generic basis gate audit for 7-qubit problem: p=1 126 CX, depth 250; p=2 252 CX, depth 482 (not mapped to real backend).
- v0.8: exact 7-qubit Walsh/Pauli decomposition used 642 CX; truncations lost the reference optimum on most/all records; ideal measured probability assigned to invalid states was about 33–41% under the tested settings.
- v0.9: ideal feasibility-preserving mixer produced 0 invalid states but 464 CX for p=1 and 856 CX for p=2 in the tested audit. Optimization runs differed; do not compare runs without fixing seed/budget/objective.
- v0.10: reduced model to 4×4 candidates (4 qubits). Original 100-pair optimum remained within this subset on five pilot records. Ideal p=2 optimum probability: 24.52%, 97.93%, 74.64%, 50.27%, 34.46%; generic basis CX count 24–28. These tasks have different numbers of tied optima.
- v0.11: artificial 5-qubit topology reported p=1 depth 72 and 19 CX, but is not physical device compilation.
- v0.12: preparations for genuine IBM target compilation, uniform-control circuit, explicit opt-in hardware execution and result collection. **Hardware results not yet available.**

## Methodological boundaries

1. Subset selection uses score marginals: it is reference-blind but derives from the score table and may make the optimization easier; do not describe results as solving the original 100-pair space.
2. Report absolute optimum probability, probability relative to uniform, number of tied optima, number of shots, and ideal-vs-hardware differences.
3. Hardware transpilation can change CX-equivalent counts and measurement fidelity. Error estimates based on independent gate errors are only heuristics.
4. The two-segment benchmark is a local problem: do not treat its second position as a full-song cadence unless it actually is.
5. Exact enumeration is inexpensive for 16 candidates and should remain the strongest control: observed successful sampling is not a speedup.
6. Backend queues and calibrations change; record actual execution date/time and software versions.

## Near-term publication question

How do hardware constraints and phase-based quantum optimization affect the probability of sampling harmonically high-scoring decisions, and what tradeoffs arise from musical candidate reduction?
