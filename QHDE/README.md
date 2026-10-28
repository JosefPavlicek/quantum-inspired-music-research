# QHDE – Quantum Harmonic Dependency Experiment, prototype 0.1

**Goal:** Investigate whether quantum interference can amplify high-scoring harmonic candidate pairs under explicit constraints, compared with uniform sampling and exact classical search.

## First step: no IBM Quantum account or QPU time required

Python 3.10+ recommended. Install NumPy:

```bash
python3 -m pip install -r requirements.txt
python3 grover_interference.py
python3 qhde_simulator.py
```

Files generated in `results/`:
- `harmonic_candidates.csv`: all 16 pairs, classical scores and simulated probabilities;
- `summary.json`: best circuit angles, mean score, probability of sampling an exact optimum.

## Important methodological limits

- The first script demonstrates Grover's interference with a **known** target, not learned harmony.
- The second script simulates **four logical qubits**, 4 chord choices × 2 positions = 16 pairs, in a p=1 QAOA-like ansatz using a **diagonal phase operator** and transverse-field mixing.
- Musical scores are **illustrative placeholders**, not extracted from corrected EMH or human judgments.
- The numerical phase operator is an ideal state-vector transformation. **This prototype has not yet been compiled to an IBM native-gate circuit**. A generic diagonal operator may be expensive to implement on hardware; efficient Hamiltonian decomposition is a separate engineering/research task.
- Parameter search uses exact state probabilities and a full classical grid. On real QPU, the objective must be estimated from finite shot counts, with hardware noise.
- This is **not** evidence of quantum advantage. The exact classical optimum is trivial for 16 pairs.

## Research roadmap

1. Validate interference and baseline using the two scripts.
2. Replace demonstration scores with the verified, corrected EMH/HARMONIX scoring function, with fixtures, tests and documented version.
3. Compile an explicit cost Hamiltonian into efficient native 1- and 2-qubit gates; compare entangling vs matched non-entangling ablations.
4. Run noiseless and noisy simulators, pre-register metrics and shot budget.
5. Only then obtain permission and execute limited shots on IBM Research_CVUT QPU.

Do not place your IBM API token in source code, files, or a chat.
