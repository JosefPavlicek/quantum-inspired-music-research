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

<!-- QHDE-CONSOLIDATED-2026-10 -->
## Research status (QHDE v0.12–v0.26)

QHDE studies quantum approximate optimization for **harmonic decision sequences** derived from the **corrected EMH** inside HARMONIX. The published standalone EMH is a frozen reproducibility baseline and must not be changed.

- **v0.19:** 4-qubit, two-segment IBM Pittsburgh benchmark, 16 instances, 16 states each. Hardware mean optimum probabilities: uniform 10.25%, p=1 33.33%, p=2 42.70%, p=3 51.10%.
- **v0.21:** Independent hardware replication on Pittsburgh. Hardware means: uniform 9.81%, p=1 34.23%, p=2 43.52%, p=3 52.46%. Reproduction does not imply quantum advantage.
- **v0.22:** Constructed 16 four-segment, 8-qubit problems (four candidates per segment; 256 states); 16/16 succeeded.
- **v0.23:** Exact Pauli-Z decomposition audit. 12/16 Hamiltonians are neighbor-local; 4/16 require higher-order/nonlocal penalty terms. The original 8-qubit cost model must remain exact; do not discard constraints to reduce circuit depth without changing the declared problem.
- **v0.24:** Optimized QAOA p=1,2,3 for all 16 in ideal simulation, preparing 36 logical circuits for the 12 local problems.
- **v0.25:** IBM Marrakesh job `dbh8j5kdgr2s73ct1100`, 48 circuits × 1,024 shots, 8 qubits, 12 local instances, charge 16 s of QPU time. Hardware mean optimum probabilities: uniform 1.204%, p=1 6.681%, p=2 10.343%, p=3 12.492%. Ideal means: 1.237%, 9.914%, 19.116%, 28.166%.
- **v0.26:** Offline hardware/ideal gap audit from v0.25. Mean hardware-to-ideal loss increases with QAOA depth. Paired p=3 vs p=2 hardware gain +2.15 percentage points (9 positive, 2 negative, 1 tied among 12). Instance-level statistical dependence and device drift remain open caveats.

### Reproducibility and important limitations

- The optimum is defined by the **modeled corrected-EMH scoring function**, not by a human-listener preference study.
- The 256-state optimization problem is easy to enumerate classically; **no quantum computational advantage** has been demonstrated.
- Some records may share the same effective energy landscape; don't assume all song records are independent optimization instances.
- Logical circuit gate counts differ from backend-transpiled physical circuit counts. Use the saved `preparation.json`/QPY and backend details for device costs.
- Store job IDs, raw result data, optimized parameters, instance manifests and test scripts in the repository; never commit IBM API credentials or the `qiskit-ibm.json` token file.

### Main entry points

From the repository root, with Python available at `HARMONIX/.venv/bin/python`:

```bash
HARMONIX/.venv/bin/python QHDE/qhde_four_segments_v22.py --limit 16
HARMONIX/.venv/bin/python QHDE/qhde_structured_qaoa_v23.py
HARMONIX/.venv/bin/python QHDE/qhde_optimize_v24.py --starts 12 --maxiter 200
HARMONIX/.venv/bin/python QHDE/qhde_ibm_v25.py --analyze
HARMONIX/.venv/bin/python QHDE/qhde_audit_v26.py
```

IBM submission is a separate, **explicitly confirmed** action. Do not resubmit existing jobs. The corresponding result artifacts live under `QHDE/results/`.

