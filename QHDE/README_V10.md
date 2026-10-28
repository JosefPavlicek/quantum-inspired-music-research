# QHDE v0.10 — Four-qubit hardware demonstrator (offline)

Add the two Python files and this README **directly inside `QHDE/`**. Do not change HARMONIX or the frozen EMH. Uses exported `QHDE/results/hooktheory_v04/scores_*.json` files; no human reference chord data, API credentials, or IBM calls.

## Purpose

Reduce the 10×10 corrected EMH pair task to a prespecified **4×4** subtask (16 candidate pairs, 4 qubits) for preliminary hardware feasibility. Candidate selection is deterministic, using the four highest **marginal mean model scores** for each position (stable numerical-index tie break). This is **model-informed selection**, NOT a neutral random sample; it changes the problem, so results cannot be compared directly to the full 100-pair benchmark. We report whether the full-space optimum is retained. We do not use HookTheory human reference harmonies when selecting candidates.

The phase operator is an exact 16-state diagonal unitary; RX mixers are used. The algorithm optimizes expected normalized score, and the report separately measures optimum probability. Two reproducible depths p=1,2 are audited. No quantum advantage is claimed.

## Run from repository root

```bash
HARMONIX/.venv/bin/python -m unittest discover -s QHDE -p 'test_hardware_v10.py' -v
HARMONIX/.venv/bin/python QHDE/qhde_hardware_v10.py --limit 5 --seed 42 --starts 64
```

Output: `QHDE/results/hardware_v10/summary.json`. Add `--skip-qiskit` for a faster NumPy-only run. All run steps are local, no QPU time consumed.

## Limitations and before real IBM hardware

- Basis transpilation counts are not device-layout aware. Next: select actual backend, transpile against its coupling map, validate estimated runtime and expected fidelity, then request authorization before submitting jobs.
- `CX` circuit counts are not guaranteed to match real backend native gates.
- Finite shot noise and hardware decoherence are not modeled.
- Four-qubit pilot is an engineering demonstrator; a 100-pair full benchmark remains a separate research task.
- The candidate-selection rule uses model scores; make this explicit in publications and compare against classical exact subproblem optimum and matched random baselines.
