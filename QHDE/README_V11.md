# QHDE v0.11 — Safe IBM backend preparation

This patch adds **no QPU execution code**. It uses QHDE v0.10's stored optimized parameters and original score inputs to transpile the exact circuit for a simulated or accessible IBM backend.

Copy `qhde_ibm_prepare_v11.py`, `test_ibm_prepare_v11.py`, and `README_V11.md` directly into existing `QHDE/`. Do not replace any directories and do not touch `HARMONIX` or frozen EMH.

## From repository root

```bash
HARMONIX/.venv/bin/python -m unittest discover -s QHDE -p 'test_ibm_prepare_v11.py' -v
HARMONIX/.venv/bin/python QHDE/qhde_ibm_prepare_v11.py --mode offline --p 1
HARMONIX/.venv/bin/python QHDE/qhde_ibm_prepare_v11.py --mode offline --p 2
```

The `offline` mode uses a synthetic **five-qubit linear-chain** target, not any specific IBM processor. `offline_audit.json` is overwritten when changing `--p`; use a distinct `--out` path if you need to keep both outputs.

For actual IBM metadata, install the client if not installed:

```bash
HARMONIX/.venv/bin/python -m pip install 'qiskit-ibm-runtime>=0.47,<1'
HARMONIX/.venv/bin/python QHDE/qhde_ibm_prepare_v11.py --mode inventory
```

This last command requires an already-configured IBM account. Set up API credentials using IBM's official local configuration workflow, **never paste API keys in chat or commit them to Git**. Some institutional accounts may require `--instance <IBM_INSTANCE_IDENTIFIER>`; confirm the exact identifier in IBM dashboard.

Once an accessible backend is known (example placeholder `BACKEND_NAME`):

```bash
HARMONIX/.venv/bin/python QHDE/qhde_ibm_prepare_v11.py --mode backend --backend BACKEND_NAME --p 1
```

This only reads public/account-visible backend configuration and transpiles locally; no sampler, estimator, jobs, measurements on hardware, or QPU time billed by this script.

**Limitations:** The prepared circuit may occupy >4 physical qubits because routing maps 4 logical wires to larger devices. `two_qubit_total` counts selected entangling gates; other multi-qubit operations may need review. Transpilation is deterministic only under fixed versions/calibration/layout/seed. The test suite checks metadata and CLI validation, not hardware results. The cost function is model-scored, and the pilot shortlist is model-informed; do not claim quantum advantage.
