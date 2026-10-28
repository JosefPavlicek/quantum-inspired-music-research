# QHDE v0.6 — Qiskit Circuit Validation

**Patch only:** copy the three files at the top level of this archive into the existing `QHDE/` directory. Do not overwrite existing v0.1–0.5 files. No changes to frozen EMH or HARMONIX.

## From repository root (Codespaces)

```bash
HARMONIX/.venv/bin/python -m pip install 'qiskit>=2.1,<3'
HARMONIX/.venv/bin/python -m unittest discover -s QHDE -p 'test_qiskit_v06.py' -v
HARMONIX/.venv/bin/python QHDE/qhde_qiskit_v06.py --limit 5
```

This assumes `QHDE/results/hooktheory_v04/scores_000.json` ... `scores_004.json` and `QHDE/results/qaoa_v05/result_000.json` ... `result_004.json` exist. Re-run QHDE v0.5 first if needed.

Expected: four unit tests and five record comparisons with `OK`. The JSON report will be at `QHDE/results/qiskit_v06/validation.json`.

## What is validated

- 7-qubit Qiskit circuit with Hadamard initial state, a full 128-entry diagonal phase gate for each QAOA cost layer and `RX(2*beta)` mixer gates.
- Same energy normalization and 28 invalid-state penalties as v0.5.
- Exact statevector amplitude and probability equivalence to the existing NumPy simulator, for both p=1 and p=2, using v0.5's optimized parameter sets.
- The scoring export is **corrected HARMONIX candidates + frozen EMH scoring**. No reference harmony is used in candidate generation.

## Important scientific limitation

`DiagonalGate` is convenient for checking mathematical equivalence but is not automatically a compact implementable oracle. Arbitrary 128-phase diagonals may synthesize to deep native circuits. **Do not submit this directly to hardware.** First transpile for the chosen IBM backend, inspect gate count/depth and estimated runtime, and investigate structured/low-locality cost Hamiltonians. The non-entangling cost approximation in v0.5 is not a matched entanglement ablation. The existing results do not demonstrate quantum advantage.

## Validation note

The package was syntax-checked and its NumPy-only interface inspected locally. Qiskit was not installable in the artifact-building environment because its Python package index was unreachable, so the actual Qiskit tests must be executed in your Codespaces before treating them as verified.

No IBM token is required and no hardware jobs are submitted.
