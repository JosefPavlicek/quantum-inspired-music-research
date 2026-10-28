# QHDE — Quantum Harmonic Dependency Experiment

Standalone experimental branch of **HARMONIX**. The published Explainable Melody Harmonizer (EMH) remains frozen. HARMONIX supplies *corrected* chord candidates while existing EMH scoring is reused without modifying frozen source. All melody inputs come from the shared `data/hooktheory/Hooktheory.json.gz` TRAIN manifest; no reference harmony is used for candidate generation.

## Scientific scope

Quantum Approximate Optimization Algorithm (QAOA) on score matrices of neighboring chord candidates, with exact classical enumeration. The full test uses 10 × 10 pairs (7-qubit encoding); the four-qubit hardware demonstrator reduces the problem to 4 × 4 pairs using deterministic model-score marginals. This **changes the problem**; the preserved full optimum has only been observed in the five initial pilot records. No quantum speedup or improved listener preference has been demonstrated.

## Reproducible pipeline

- `qhde_hooktheory_export.py`: corrected vocabulary + HookTheory data, 100 two-position scores per record.
- `qhde_qaoa_v05.py`: seven-qubit numerical QAOA pilot.
- `qhde_qiskit_v06.py`: Qiskit equivalence validation.
- `qhde_hardware_v10.py`: four-qubit 16-state demonstrator, score-based subset, stable seeds and optimized parameters.
- `qhde_ibm_prepare_v11.py`: inventory / basic QPU transpilation.
- `qhde_ibm_v12.py`: calibration-aware transpilation and opt-in hardware execution.

## v0.12: prepare only

From repository root, with IBM credentials *already saved outside Git*:

```bash
HARMONIX/.venv/bin/python -m unittest discover -s QHDE -p 'test_ibm_v12.py' -v
HARMONIX/.venv/bin/python QHDE/qhde_ibm_v12.py --p 1
```

This checks `ibm_pittsburgh` and `ibm_marrakesh`, selects the candidate with fewer compiled two-qubit gates (queue as tie-break), saves `QHDE/results/ibm_v12/preparation.json` and `prepared_circuits.qpy`. **No QPU job is submitted**. Inspect preparation metrics, qubit calibration data, budget and provider availability before proceeding.

## Hardware submission — *only after deliberate approval*

`--submit` alone is insufficient. A real job is sent **only** with both `--submit` and `--confirm-spend-QPU`:

```bash
HARMONIX/.venv/bin/python QHDE/qhde_ibm_v12.py --submit --confirm-spend-QPU
```

This sends exactly two measured circuits (uniform control and QAOA p=1) with 1024 shots each, unless reconfigured **before preparing**. Note that submitting a job can incur charge/time use; no precise runtime is promised from gate counts. The script saves `submitted_job.json`. Do not submit twice if the first request errors before returning an ID; check the IBM dashboard/jobs first.

Collect a completed job without submitting:

```bash
HARMONIX/.venv/bin/python QHDE/qhde_ibm_v12.py --collect
```

Measurement counts and success fractions are saved in `measured_results.json`. Compare QPU empirical probabilities with the uniform control and ideal pilot model. Qiskit's transpilation uses currently available backend metadata, not an accurate predictive simulation of hardware noise.

## Security / reproducibility

Do not commit credentials, API keys, `~/.qiskit/qiskit-ibm.json`, or private music archives. `.gitignore` should exclude `__pycache__/`, `*.pyc`, `*.qpy`, `.env` and secret files. Commit sanitized JSON metrics and source code; avoid sharing backend account/instance IDs unnecessarily. Preserve the record identifier, seed, QAOA angles, compilation level, actual backend and snapshot of relevant calibration statistics.

## Previous studies

Version-specific research notes `README_Vxx.md` can be removed after consolidating the experiment narrative into this file and `RESEARCH_SUMMARY.md`. Keep scripts, parameter files, test results, and Git history: those are needed for reproducibility.
