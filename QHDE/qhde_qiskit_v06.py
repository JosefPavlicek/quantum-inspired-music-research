"""QHDE v0.6: Qiskit circuit and exact NumPy-vs-Qiskit statevector checks.

Read-only; never connects to a provider or sends hardware jobs. Run from repository root.
Qiskit 2.x expected. Circuit is a *generic diagonal cost unitary*, which may
transpile into many two-qubit gates. No hardware performance claim.
"""
import argparse
import json
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from qhde_qaoa_v05 import (DIM, N_QUBITS, load_problem, energies_from_scores,
                          statevector as numpy_statevector, metrics)


def make_circuit(energies, params, measurement=False):
    """Use same computational-basis ordering and phase convention as v0.5.

    Qiskit q0 is the least significant bit of the statevector index.
    Each layer: diag(exp(-i gamma E)) then Rx(2 beta) on all seven qubits.
    """
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import DiagonalGate
    energies = np.asarray(energies, dtype=float)
    params = np.asarray(params, dtype=float)
    if energies.shape != (DIM,) or not np.all(np.isfinite(energies)):
        raise ValueError('Expected 128 finite energies')
    if len(params) not in (2, 4) or not np.all(np.isfinite(params)):
        raise ValueError('Expected 2 (p=1) or 4 (p=2) finite parameters')
    circuit = QuantumCircuit(N_QUBITS, N_QUBITS) if measurement else QuantumCircuit(N_QUBITS)
    circuit.h(range(N_QUBITS))
    for k in range(0, len(params), 2):
        gamma, beta = params[k:k+2]
        circuit.append(DiagonalGate(np.exp(-1j * gamma * energies).tolist()), range(N_QUBITS))
        circuit.rx(2 * beta, range(N_QUBITS))
    if measurement:
        circuit.measure(range(N_QUBITS), range(N_QUBITS))
    return circuit


def validate_one(scores_file, result_file, atol=1e-9):
    from qiskit.quantum_info import Statevector
    source, scores = load_problem(scores_file)
    energy = energies_from_scores(scores)
    result = json.loads(Path(result_file).read_text(encoding='utf-8'))
    if result.get('record_id') != source.get('record_id'):
        raise ValueError('Record ID mismatch between scores and v0.5 optimization')
    report = []
    for p in (1, 2):
        key = f'qaoa_p{p}_full'
        params = result['models'][key]['params']
        qiskit_state = np.asarray(Statevector.from_instruction(make_circuit(energy, params)).data)
        numpy_state = numpy_statevector(energy, params)
        max_amp_error = float(np.max(np.abs(qiskit_state - numpy_state)))
        probability_error = float(np.max(np.abs(np.abs(qiskit_state)**2 - np.abs(numpy_state)**2)))
        if max_amp_error > atol or probability_error > atol:
            raise AssertionError(f'{key}: statevector mismatch {max_amp_error}')
        calculated = metrics(np.abs(qiskit_state)**2, scores)
        stored = result['models'][key]['metrics']
        for name, val in calculated.items():
            other = stored[name]
            if val is None or other is None:
                if val is not other:
                    raise AssertionError(f'{key}: {name} missing metric mismatch')
            elif abs(val-other) > atol:
                raise AssertionError(f'{key}: stored metric mismatch {name}')
        report.append({'model': key, 'max_amplitude_absolute_error': max_amp_error,
                       'max_probability_absolute_error': probability_error,
                       'valid_probability': calculated['valid_probability'],
                       'optimum_probability_given_valid': calculated['optimum_probability_given_valid'],
                       'invalid_probability': calculated['invalid_probability'],
                       'circuit_instructions_before_transpile': len(make_circuit(energy, params).data)})
    return {'score_file':str(scores_file), 'record_id':source.get('record_id'), 'comparisons':report}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scores-dir', default='QHDE/results/hooktheory_v04')
    parser.add_argument('--v05-dir', default='QHDE/results/qaoa_v05')
    parser.add_argument('--out', default='QHDE/results/qiskit_v06')
    parser.add_argument('--limit', type=int, default=5)
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error('--limit must be >=1')
    scores = sorted(Path(args.scores_dir).glob('scores_*.json'))[:args.limit]
    if not scores:
        parser.error('No scores_*.json found')
    rows = []
    for index, path in enumerate(scores):
        result = Path(args.v05_dir) / f'result_{index:03d}.json'
        if not result.is_file():
            parser.error(f'Cannot find {result}; run QHDE v0.5 first')
        row = validate_one(path, result)
        rows.append(row)
        print(f'OK: {path.name} / {row["record_id"]} / p=1,2')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = {'version':'QHDE-v0.6', 'simulation_only':True,
              'hardware_jobs_submitted':0,
              'warning':'Generic DiagonalGate is not an efficient native hardware cost oracle. Transpile and assess depth before QPU use.',
              'records':rows}
    dest = out / 'validation.json'
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Saved', dest)

if __name__ == '__main__':
    main()
