# QHDE v0.9 — Feasibility-preserving mixer (offline)

This patch adds a separate **diagnostic** experiment without modifying original EMH, corrected HARMONIX, or previous QHDE versions.

## Why

v0.8 returned 33–41% invalid samples using fixed parameters and a standard X mixer on 7 qubits. That does not prove penalty failure in an optimized circuit. This patch tests another algorithm: uniform superposition of **exactly the 100 feasible pairs**, followed by a mixer that mathematically preserves that subspace.

The mixer is `exp(-i * beta * |s><s|)` for uniform feasible state `|s>`. Its invalid probability is zero in exact statevector arithmetic **by construction** — this is NOT a discovered quantum advantage. The nontrivial question is whether it is implementable economically. The required exact state preparation/reflection may be expensive.

## Install

Copy `qhde_feasible_v09.py`, `test_feasible_v09.py`, `README_V09.md` directly into `QHDE/`. Ignore any `__pycache__`.

From repository root:

```bash
HARMONIX/.venv/bin/python -m unittest discover -s QHDE -p 'test_feasible_v09.py' -v
HARMONIX/.venv/bin/python QHDE/qhde_feasible_v09.py --limit 5
```

Optional Qiskit verification and **offline** transpilation (start with a single score export, may be computationally costly):

```bash
HARMONIX/.venv/bin/python QHDE/qhde_feasible_v09.py --limit 1 --starts 12 --qiskit-check --transpile
```

Inspect `QHDE/results/feasible_v09/summary.json`.

## Evaluation cautions

- Compare optimal-sample probability against the correct uniform **valid** baseline (e.g., 1/100 for one exact optimum).
- Do not compare with p=1/p=2 of v0.5 without matching optimization budgets.
- Runtime and transpiled two-qubit gate counts are essential. This construction may lose on hardware despite mathematically perfect feasibility.
- The score source is HookTheory TRAIN through corrected HARMONIX candidate generation and frozen EMH scoring. No reference harmony is used during generation.
- No IBM API access, no quantum device time used.
