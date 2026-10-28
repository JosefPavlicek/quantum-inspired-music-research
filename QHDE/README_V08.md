# QHDE v0.8 — offline Walsh-Z Hamiltonian compression

Add the three files to `QHDE/`. Do not overwrite HARMONIX or frozen EMH.

## Commands (from repository root)

```bash
HARMONIX/.venv/bin/python -m unittest discover -s QHDE -p 'test_structured_v08.py' -v
HARMONIX/.venv/bin/python QHDE/qhde_structured_v08.py --limit 5
```

Outputs: `QHDE/results/structured_v08/summary.json`.

## What is actually measured

Scores are from `scores_*.json` exported through corrected HARMONIX candidates and frozen EMH scoring. Index `10*a_index+b_index` maps 100 legal pairs into states 0..99 of 7 qubits; states 100..127 have a deliberately penalized synthetic score. For scientific rigor, the full treatment of 28 invalid states must be harmonized with v0.5 before comparing optimized parameter results.

The exact Walsh-Hadamard expansion expresses a 7-qubit diagonal energy Hamiltonian in products of Pauli-Z operators. Exact expansion preserves energies and the QAOA circuit up to global phase. A truncated version keeps the strongest 16 or 32 nonconstant coefficients; `degree2` retains only constant, one-body, and pairwise terms. These are *approximations*, and may change score ordering.

Hardware resource audit uses `basis_gates=['rz','sx','x','cx']` WITHOUT device coupling map or calibration. Thus CX counts are abstract, not actual backend-native ECR counts. We do NOT submit jobs or consume QPU quota.

Default gamma=.7 and beta=.4 are *fixed diagnostic values*, NOT optimized v0.5 parameters. Do not compare optimization success against v0.5 based on these numbers.

**Important limitation:** this is a Walsh-Z compression of the score table, not yet a derivation of semantically interpretable local melody/transition terms. A smaller CX count is not guaranteed: unoptimized parity gadgets can cost more than DiagonalGate synthesis. Select on both music fidelity and gate count; never claim quantum advantage from compression alone.
