"""QHDE v0.10: deterministic four-qubit HookTheory hardware demonstrator.
Offline only. Reads v0.4 score exports, never accesses IBM or reference harmony.
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np


def build_problem(data):
    if data.get('candidate_variant') != 'corrected' or data.get('candidate_count') != 10:
        raise ValueError('Requires HARMONIX corrected 10-candidate vocabulary')
    scores = np.full((10, 10), np.nan)
    for row in data['pairs']:
        i, j = int(row['a_index']), int(row['b_index'])
        if not (0 <= i < 10 and 0 <= j < 10) or np.isfinite(scores[i, j]):
            raise ValueError('Invalid or duplicate pair index')
        scores[i, j] = float(row['score'])
    if not np.isfinite(scores).all():
        raise ValueError('Expected full 10x10 score matrix')
    # Predeclared, reference-blind selection rule: descending mean score per position.
    # This uses the MODEL'S score matrix, not human reference harmony.
    # Stable index tie-breaks; no information about which pair wins is used.
    a = sorted(range(10), key=lambda i: (-float(np.mean(scores[i, :])), i))[:4]
    b = sorted(range(10), key=lambda j: (-float(np.mean(scores[:, j])), j))[:4]
    sub = scores[np.ix_(a, b)]
    span = float(np.ptp(sub))
    if span < 1e-12:
        raise ValueError('All selected pair scores tied')
    # basis index = 4*local_first + local_second; q0 LSB in Qiskit
    energies = -(sub.reshape(16) - float(np.min(sub))) / span
    full_best = float(np.max(scores))
    included = bool(np.any(np.isclose(sub, full_best, atol=1e-10, rtol=0)))
    return {'a_indices':a,'b_indices':b,'subscores':sub,'energies':energies,
            'full_optimum':full_best,'subset_optimum':float(np.max(sub)),
            'full_optimum_represented':included}


def np_state(energies, params):
    state = np.full(16, 0.25+0j)
    for layer in range(len(params)//2):
        gamma, beta = params[2*layer:2*layer+2]
        state *= np.exp(-1j*gamma*energies)
        c,s=np.cos(beta),-1j*np.sin(beta)
        for q in range(4):
            step=1<<q
            x=state.reshape(-1,2*step)
            lo=x[:,:step].copy();hi=x[:,step:].copy()
            x[:,:step]=c*lo+s*hi
            x[:,step:]=s*lo+c*hi
    return state


def make_circuit(energies, params, measure=False):
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import DiagonalGate
    if len(energies)!=16 or len(params) not in (2,4):
        raise ValueError('Expected 16 energies and 2/4 parameters')
    qc=QuantumCircuit(4,4) if measure else QuantumCircuit(4)
    qc.h(range(4))
    for layer in range(len(params)//2):
        gamma,beta=params[2*layer:2*layer+2]
        qc.append(DiagonalGate(np.exp(-1j*gamma*np.asarray(energies)).tolist()),range(4))
        qc.rx(2*float(beta),range(4))
    if measure: qc.measure(range(4),range(4))
    return qc


def objective(energies, params):
    probs=np.abs(np_state(energies,params))**2
    return -float(np.dot(probs,energies))


def optimize(energies,p,seed=42,starts=64):
    rng=np.random.default_rng(seed)
    params_list=[np.zeros(2*p)] + [rng.uniform(0,2*np.pi,2*p) for _ in range(starts)]
    best=max(params_list,key=lambda x: objective(energies,x)).copy()
    val=objective(energies,best)
    for step in (0.4,0.12,0.035):
        for _ in range(8):
            moved=False
            for axis in range(len(best)):
                for direction in (-1,1):
                    cand=best.copy();cand[axis]=(cand[axis]+direction*step)%(2*np.pi)
                    obj=objective(energies,cand)
                    if obj>val+1e-13: best,val,moved=cand,obj,True
            if not moved: break
    return best,val


def evaluate(path,seed=42,starts=64,audit=True):
    data=json.loads(Path(path).read_text(encoding='utf8'))
    p=build_problem(data)
    subs=p['subscores'].reshape(16)
    optimum=np.max(subs);optmask=np.isclose(subs,optimum,rtol=0,atol=1e-10)
    result={'score_file':str(path),'record_id':data.get('record_id'),
            'selection':'top4 marginal mean score per position, stable tie-break',
            'a_indices':p['a_indices'],'b_indices':p['b_indices'],
            'full_optimum_represented':p['full_optimum_represented'],
            'full_optimum':p['full_optimum'], 'subset_optimum':p['subset_optimum'],
            'uniform_optimum_probability':float(optmask.mean()),'models':{}}
    for depth in (1,2):
        params,val=optimize(p['energies'],depth,seed+100*depth,starts)
        probs=np.abs(np_state(p['energies'],params))**2
        row={'params':params.tolist(),'expected_normalized_score':val,
             'optimum_probability':float(probs[optmask].sum()),
             'expected_raw_score':float(np.dot(probs,subs)),
             'probabilities':probs.tolist(),'invalid_probability':0.0}
        if audit:
            from qiskit.quantum_info import Statevector
            from qiskit import transpile
            sv=Statevector.from_instruction(make_circuit(p['energies'],params)).data
            row['statevector_max_error']=float(np.max(np.abs(sv-np_state(p['energies'],params))))
            qc=transpile(make_circuit(p['energies'],params),basis_gates=['rz','sx','x','cx'],optimization_level=1)
            row['cx_count']=int(qc.count_ops().get('cx',0))
            row['transpiled_depth']=int(qc.depth())
            row['topology_aware']=False
        result['models'][f'p{depth}']=row
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input-dir',default='QHDE/results/hooktheory_v04')
    ap.add_argument('--out',default='QHDE/results/hardware_v10')
    ap.add_argument('--limit',type=int,default=5)
    ap.add_argument('--seed',type=int,default=42)
    ap.add_argument('--starts',type=int,default=64)
    ap.add_argument('--skip-qiskit',action='store_true')
    args=ap.parse_args()
    if args.limit<1 or args.starts<0: ap.error('Invalid limit/starts')
    paths=sorted(Path(args.input_dir).glob('scores_*.json'))[:args.limit]
    if not paths: ap.error('No HookTheory scores found')
    output=Path(args.out);output.mkdir(parents=True,exist_ok=True)
    results=[]
    for index,path in enumerate(paths):
        row=evaluate(path,args.seed+1000*index,args.starts,not args.skip_qiskit)
        results.append(row)
        for name,model in row['models'].items():
            print(f'{path.name} {name}: uniform={row["uniform_optimum_probability"]:.2%} '
                  f'QAOA={model["optimum_probability"]:.2%} '
                  f'CX={model.get("cx_count","n/a")} '
                  f'full_optimum_in_subset={row["full_optimum_represented"]}')
    report={'version':'QHDE-v0.10','simulation_only':True,'qpu_jobs':0,
            'seed':args.seed,'starts':args.starts,
            'warning':'Deterministic score-based reduction changes the problem. No quantum advantage claim. CX count excludes physical backend topology.',
            'records':results}
    (output/'summary.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print('Saved',output/'summary.json')

if __name__=='__main__': main()
