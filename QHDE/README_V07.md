# QHDE v0.7 — offline hardware-feasibility *pre-audit*

Add these three files to the existing `QHDE/` directory. This stage **never connects to IBM** and spends **zero QPU seconds**.

From repository root:

```bash
HARMONIX/.venv/bin/python -m unittest discover -s QHDE -p 'test_hardware_audit_v07.py' -v
HARMONIX/.venv/bin/python QHDE/qhde_hardware_audit_v07.py --limit 1 --basis cx --level 1
```

To evaluate all five records (may take longer):

```bash
HARMONIX/.venv/bin/python QHDE/qhde_hardware_audit_v07.py --limit 5 --basis cx --level 1
```

Outputs `QHDE/results/hardware_audit_v07/resource_audit.json`, including circuit depth, basis gate count, and two-qubit gate count for p=1 and p=2.

**Critical limitation:** This is *not* a real IBM backend transpilation. It only converts to a representative IBM-like gate set; no qubit connectivity, routing, calibrated error rates, circuit duration, shot cost or fidelity is considered. Do not infer actual QPU feasibility from this alone. For the next stage, obtain a real backend target, choose a layout and perform topology-aware transpilation before any submission.

For research: the v0.6 dense `DiagonalGate` encodes all 128 energies and may lead to a high gate count. Compare with a structured/low-order energy decomposition rather than changing the score function without documenting the approximation error. The v0.5 'separable' control changes the objective and is **not** a matched entanglement ablation.
