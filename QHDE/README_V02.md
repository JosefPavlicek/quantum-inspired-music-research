# QHDE v0.2 — Score-interface bridge (offline)

**Status:** tested NumPy simulator, not IBM Quantum / Qiskit implementation. The bundled scores are **demonstration-only** and do not originate from corrected EMH. QHDE does not yet import HARMONIX functions.

This version adds a traceable score-table input so corrected EMH can provide actual evaluations without duplicating its music theory.

## How to run

From `QHDE/`:

```bash
pip install -r requirements.txt
python -m unittest -v test_qhde_v02.py
python qhde_from_scores.py --input data/example_scores.json --out results/v02
```

## Contract for corrected EMH integration

Supply JSON with `source` (specific EMH commit/model/version), `chords_A`, `chords_B`, and `pair_scores`, an n × n matrix (rows = A, columns = B). `n` must be the same power of two in both positions. Entries are finite real utilities; larger is better. State index is `A_index + n * B_index`. Also record melody context, scoring weights, chord representation, and provenance, preferably in additional JSON fields.

The producer must compute scores from the actual corrected EMH model; this prototype does **not** fabricate them. Non-diatonic chords and sevenths are represented by whatever identifiers the producer provides.

## Scientific safeguards

- All `results/v02` data from the example is illustrative, NOT evidence of music quality or quantum advantage.
- QAOA parameters are searched exhaustively and classically over a grid, with a known exact classical optimum as a control.
- QPU time consumption: **zero**.
- Before attempting IBM execution: inspect current HARMONIX code, implement a verified EMH export adapter, pin Qiskit dependencies, test transpilation and QPU time estimates, and confirm allocation.
- Don't overwrite HARMONIX or Explainable_Melody_Harmonizer. Add only the contents of this QHDE folder.
