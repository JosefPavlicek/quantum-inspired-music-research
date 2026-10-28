"""QHDE v0.9: EXACT feasibility-preserving mixer; offline only.

Research control, not evidence of quantum advantage nor hardware efficiency.
Scores originate from corrected HARMONIX HookTheory exports.
Index encoding: index=10*a_index+b_index, 0..99 allowed, 100..127 forbidden.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import numpy as np

N = 7
DIM = 128
VALID = 100


def read_export(path):
    obj = json.loads(Path(path).read_text(encoding='utf8'))
    if obj.get('candidate_variant') != 'corrected' or obj.get('candidate_count') != 10:
        raise ValueError('Expected corrected HARMONIX 10-candidate scores')
    scores = np.full(VALID, np.nan)
    for row in obj['pairs']:
        i, j = int(row['a_index']), int(row['b_index'])
        if not (0 <= i < 10 and 0 <= j < 10):
            raise ValueError('Invalid pair index')
        ix = 10*i + j
        if np.isfinite(scores[ix]):
            raise ValueError('Duplicated candidate pair')
        scores[ix] = float(row['score'])
    if len(obj['pairs']) != VALID or not np.isfinite(scores).all():
        raise ValueError('Expected exactly 100 finite pair scores')
    return obj, scores


def normalized_energies(scores):
    delta = np.ptp(scores)
    if delta <= 1e-12:
        raise ValueError('All candidate scores tied')
    return -(scores - scores.min())/delta


def feasible_initial():
    v = np.zeros(DIM, dtype=complex)
    v[:VALID] = 1 / math.sqrt(VALID)
    return v


def projector_mixer(state, beta):
    """exp(-i beta |s><s|), where |s> is uniform on 100 feasible states.
    This is a feasibility-preserving unitary, NOT the standard X mixer.
    """
    s = feasible_initial()
    return state + np.expm1(-1j*beta) * s * np.vdot(s, state)


def statevector(energies, params):
    if len(params) < 2 or len(params) % 2:
        raise ValueError('gamma, beta must be supplied for each layer')
    e = np.zeros(DIM, dtype=float)
    e[:VALID] = energies
    psi = feasible_initial()
    for gamma, beta in np.asarray(params).reshape(-1, 2):
        psi = psi * np.exp(-1j * gamma * e)
        psi = projector_mixer(psi, beta)
    return psi


def stats(psi, scores):
    p = abs(psi)**2
    tied = np.flatnonzero(np.isclose(scores, max(scores), rtol=0, atol=1e-10))
    top10 = np.argsort(-scores, kind='stable')[:10]
    return {
        'invalid_probability':float(p[VALID:].sum()),
        'valid_probability':float(p[:VALID].sum()),
        'optimum_probability':float(p[tied].sum()),
        'top10_probability':float(p[top10].sum()),
        'expected_score':float(p[:VALID] @ scores),
        'n_optima':int(len(tied)),
    }


def optimize(energies, depth, seed=42, starts=64):
    rng = np.random.default_rng(seed)
    def objective(v):
        return float(np.sum(abs(statevector(energies,v)[:VALID])**2 * energies))
    candidates = [np.zeros(2*depth)] + [rng.uniform(-np.pi,np.pi,2*depth) for _ in range(starts)]
    best = min(candidates, key=objective).copy()
    val = objective(best)
    for step in (0.5,0.16,0.05):
        for _ in range(5):
            improved = False
            for axis in range(2*depth):
                for sign in (-1,1):
                    trial = best.copy()
                    trial[axis] = (trial[axis]+sign*step+np.pi)%(2*np.pi)-np.pi
                    x = objective(trial)
                    if x < val - 1e-13:
                        best, val, improved = trial, x, True
            if not improved: break
    return best, val


def qiskit_circuit(energies, params):
    """Exact logical circuit; state preparation + reflection can be EXPENSIVE.
    Optional Qiskit dependency; the script runs NumPy checks without Qiskit.
    """
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import StatePreparation, DiagonalGate
    qc = QuantumCircuit(N)
    prep = StatePreparation(feasible_initial())
    qc.append(prep, range(N))
    e = np.zeros(DIM)
    e[:VALID] = energies
    for gamma, beta in np.asarray(params).reshape(-1,2):
        qc.append(DiagonalGate(np.exp(-1j*gamma*e)), range(N))
        qc.append(prep.inverse(), range(N))
        for q in range(N): qc.x(q)
        qc.mcp(-float(beta), list(range(N-1)), N-1)
        for q in range(N): qc.x(q)
        qc.append(prep, range(N))
    return qc


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input-dir',default='QHDE/results/hooktheory_v04')
    ap.add_argument('--out',default='QHDE/results/feasible_v09')
    ap.add_argument('--limit',type=int,default=5)
    ap.add_argument('--starts',type=int,default=64)
    ap.add_argument('--seed',type=int,default=42)
    ap.add_argument('--qiskit-check',action='store_true',help='Cross-check Qiskit statevector (offline)')
    ap.add_argument('--transpile',action='store_true',help='Estimate CX count for exact feasible circuit (offline)')
    args=ap.parse_args(argv)
    paths=sorted(Path(args.input_dir).glob('scores_*.json'))[:args.limit]
    if not paths: ap.error('No scores_*.json inputs found')
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    results=[]
    for ix, path in enumerate(paths):
        source,scores=read_export(path)
        energies=normalized_energies(scores)
        optimum=int(np.sum(np.isclose(scores,scores.max(),rtol=0,atol=1e-10)))
        entry={'file':path.name,'record_id':source.get('record_id'),
               'uniform_valid_optimum_probability':optimum/VALID,'depths':{}}
        for depth in (1,2):
            params,objective=optimize(energies,depth,seed=args.seed+ix*100+depth,starts=args.starts)
            psi=statevector(energies,params)
            item={'params':params.tolist(),'optimized_normalized_energy':objective,
                  'metrics':stats(psi,scores)}
            if args.qiskit_check or args.transpile:
                qc=qiskit_circuit(energies,params)
                if args.qiskit_check:
                    from qiskit.quantum_info import Statevector
                    actual=Statevector.from_instruction(qc).data
                    overlap=np.vdot(actual,psi)
                    actual=actual*(overlap/abs(overlap)) if abs(overlap)>0 else actual
                    item['qiskit_statevector_max_abs_error']=float(max(abs(psi-actual)))
                    if item['qiskit_statevector_max_abs_error']>1e-8:
                        raise RuntimeError('Qiskit/NumPy mismatch')
                if args.transpile:
                    from qiskit import transpile
                    t=transpile(qc,basis_gates=['rz','sx','x','cx'],optimization_level=1,seed_transpiler=42)
                    item['resource_audit']={'depth':t.depth(),'cx':int(t.count_ops().get('cx',0)),
                                            'operations':{str(k):int(v) for k,v in t.count_ops().items()},
                                            'backend_topology_aware':False}
            entry['depths'][f'p{depth}']=item
            m=item['metrics']
            msg=f"{path.name} p={depth}: optimum={m['optimum_probability']:.2%}, invalid={m['invalid_probability']:.3%}"
            if 'resource_audit' in item:msg+=f", CX={item['resource_audit']['cx']}"
            print(msg,flush=True)
        results.append(entry)
    target=out/'summary.json'
    target.write_text(json.dumps({'version':'QHDE-v0.9','experiment':'exact_feasible_subspace_projector_mixer',
        'no_hardware_calls':True,'simulation_only':True,'records':results,
        'warnings':['Mixer is not standard X mixer; do not compare cost fairness without resource accounting.',
                    'Exact feasible preparation/reflection may be more expensive than v0.7.',
                    'Only p=1,p=2 and limited random-restart classical search; no quantum advantage claim.']},
        ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Saved',target)

if __name__=='__main__':main()
