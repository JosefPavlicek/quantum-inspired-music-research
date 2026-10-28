"""QHDE v0.7: entirely OFFLINE basis-gate resource audit of v0.6 circuits.

No IBM credentials, network, Runtime, or jobs. A basis-only compilation is NOT
backend-aware: topology, calibrations, routing, noise and actual runtime unknown.
"""
import argparse
import json
import sys
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from qhde_qaoa_v05 import load_problem, energies_from_scores
from qhde_qiskit_v06 import make_circuit

BASIS = {'cx': ['rz', 'sx', 'x', 'cx'], 'ecr': ['rz', 'sx', 'x', 'ecr']}

def audit(scores_file, result_file, basis='cx', level=1):
    from qiskit import transpile
    if basis not in BASIS: raise ValueError('Unknown basis')
    if level not in (0,1,2,3): raise ValueError('Invalid optimization level')
    source, scores = load_problem(scores_file)
    saved = json.loads(Path(result_file).read_text(encoding='utf-8'))
    if source.get('record_id') != saved.get('record_id'):
        raise ValueError('Mismatched record ID between scores and v0.5 results')
    energy = energies_from_scores(scores)
    rows = []
    for p in (1, 2):
        params = saved['models'][f'qaoa_p{p}_full']['params']
        original = make_circuit(energy, params, measurement=False)
        compiled = transpile(original, basis_gates=BASIS[basis], optimization_level=level, seed_transpiler=42)
        ops = {str(k): int(v) for k,v in compiled.count_ops().items()}
        two_qubit = sum(1 for inst in compiled.data if inst.operation.num_qubits == 2)
        multi_qubit = sum(1 for inst in compiled.data if inst.operation.num_qubits > 2)
        rows.append({'p': p, 'original_depth': original.depth(),
                     'basis_depth': compiled.depth(), 'basis_size': compiled.size(),
                     'two_qubit_gates':two_qubit, 'greater_than_two_qubit_gates':multi_qubit,
                     'gate_counts':ops})
    return {'record_id':source.get('record_id'), 'input':str(scores_file),
            'basis':basis, 'optimization_level':level,
            'audit_type':'offline_basis_only_NO_HARDWARE_TOPOLOGY',
            'hardware_jobs_submitted':0, 'results':rows}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scores-dir',default='QHDE/results/hooktheory_v04')
    parser.add_argument('--v05-dir',default='QHDE/results/qaoa_v05')
    parser.add_argument('--out',default='QHDE/results/hardware_audit_v07')
    parser.add_argument('--limit',type=int,default=1)
    parser.add_argument('--basis',choices=list(BASIS),default='cx')
    parser.add_argument('--level',type=int,choices=[0,1,2,3],default=1)
    args=parser.parse_args(argv)
    if args.limit<1: parser.error('--limit must be positive')
    scores=sorted(Path(args.scores_dir).glob('scores_*.json'))[:args.limit]
    if not scores: parser.error('No score files found')
    output=[]
    for idx, path in enumerate(scores):
        v05=Path(args.v05_dir)/f'result_{idx:03d}.json'
        if not v05.is_file():parser.error(f'Missing {v05}; run v0.5')
        row=audit(path,v05,args.basis,args.level)
        output.append(row)
        for r in row['results']:
            print(f"{path.name} p={r['p']}: depth={r['basis_depth']} 2q={r['two_qubit_gates']} gates={r['basis_size']}",flush=True)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    target=out/'resource_audit.json'
    target.write_text(json.dumps({'version':'QHDE-v0.7','hardware_jobs_submitted':0,
          'limitations':'Basis-only: no backend connectivity, routing, timing, fidelity or QPU execution',
          'records':output},indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print('Saved',target)

if __name__=='__main__':main()
