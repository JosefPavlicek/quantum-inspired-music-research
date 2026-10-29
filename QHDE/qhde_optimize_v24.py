"""QHDE v0.24: offline variational parameter optimization for 8-qubit 4-segment QAOA.

Reads v0.22 instances and v0.23 exact locality audit. Optimizes expected energy,
not optimum-hit probability; reports both without optimizing on the latter.
ONLY the 12 exact-chain-local cases are prepared for later hardware feasibility.
NO IBM credentials/backend access or QPU submission.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from qhde_structured_qaoa_v23 import analyze, make_circuit

SRC=Path('QHDE/results/four_segments_v22')
AUDIT=Path('QHDE/results/structured_v23/audit.json')
OUT=Path('QHDE/results/optimize_v24')
N=256


def simulate(energy, params, p):
    """Independent numpy simulation, little-endian state ordering, RX mixer."""
    energy=np.asarray(energy, dtype=float)
    if energy.shape!=(N,) or not np.isfinite(energy).all(): raise ValueError('Invalid energy vector')
    params=np.asarray(params,float)
    if params.shape!=(2*p,): raise ValueError('Expected [gamma_0..gamma_p-1,beta_0..beta_p-1]')
    state=np.ones(N,complex)/16.
    for gamma,beta in zip(params[:p],params[p:]):
        state*=np.exp(-1j*gamma*energy)
        co=np.cos(beta); si=-1j*np.sin(beta)
        for q in range(8):
            view=state.reshape(-1,2**(q+1)); lo=view[:,:2**q].copy(); hi=view[:,2**q:].copy()
            view[:,:2**q]=co*lo+si*hi
            view[:,2**q:]=si*lo+co*hi
    return np.abs(state)**2


def get_optimal(energy, feasible):
    candidates=np.flatnonzero(feasible)
    if not len(candidates): raise ValueError('No feasible state')
    best=float(np.min(energy[candidates]))
    return candidates[np.isclose(energy[candidates],best,atol=1e-9,rtol=0)]


def optimize(energy, feasible, p, starts=12, maxiter=200, seed=42, previous=None):
    energy=np.asarray(energy,float); feasible=np.asarray(feasible,bool)
    opt=get_optimal(energy,feasible)
    # The cost includes infeasibility penalties. Unconstrained RX QAOA can sample infeasible states.
    # Expected cost is the training objective; probability of feasible optimum is evaluation ONLY.
    rng=np.random.default_rng(seed)
    guesses=[]
    if previous is not None:
        prev=np.asarray(previous,float)
        if prev.shape!=(2*(p-1),):raise ValueError('Bad warm start')
        guesses.append(np.concatenate([prev[:p-1],[0.0],prev[p-1:],[0.0]]))
    for i in range(starts): guesses.append(rng.uniform(0,2*np.pi,2*p))
    best=None
    def fun(x): return float(simulate(energy,x,p)@energy)
    bounds=[(0,2*np.pi)]*(2*p)
    for idx,x in enumerate(guesses):
        res=minimize(fun,x,method='L-BFGS-B',bounds=bounds,options={'maxiter':maxiter,'ftol':1e-11})
        value=float(fun(res.x))
        if best is None or value<best['expected_energy']-1e-12:
            prob=simulate(energy,res.x,p)
            best={'params':[float(v) for v in res.x], 'expected_energy':value,
                  'ideal_optimum_probability':float(prob[opt].sum()),
                  'ideal_feasible_probability':float(prob[feasible].sum()),
                  'n_optimal_states':int(len(opt)),
                  'optimizer_success':bool(res.success), 'optimizer_message':str(res.message),
                  'optimizer_nfev_best_start':int(res.nfev),'best_start_index':idx}
    best['starts_random']=starts;best['starts_total']=len(guesses);best['maxiter']=maxiter
    return best


def run(source=SRC,audit=AUDIT,out=OUT,starts=12,maxiter=200,seed=42,limit=16,export_qpy=True):
    source=Path(source);audit=Path(audit);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    manifest_file=source/'manifest.json'
    audit_data=json.loads(audit.read_text(encoding='utf-8'))
    manifest=json.loads(manifest_file.read_text(encoding='utf-8'))
    expected=hashlib.sha256(manifest_file.read_bytes()).hexdigest()
    if expected!=audit_data.get('source_manifest_sha256'):
        raise ValueError('v0.22 manifest differs from audited v0.23; refuse mismatched inputs')
    audited={r['record_id']:r for r in audit_data['records']}
    records=[]; circuits=[]; table=[]
    for i,row in enumerate(manifest['records'][:limit]):
        if row.get('status')!='ok':continue
        rid=row['record_id']; ar=audited.get(rid)
        if ar is None:raise ValueError(f'Missing locality audit: {rid}')
        item=json.loads((source/row['file']).read_text(encoding='utf-8'))
        energy=np.array(item['energies_256'],float)
        feasible=np.array([s is not None for s in item['scores_256']],bool)
        coeff,nonzero,higher,err=analyze(energy)
        if err>1e-9 or bool(higher)!=bool(ar['n_nonlocal_z_terms']):
            raise ValueError(f'Energy/locality mismatch: {rid}')
        if int(feasible.sum())!=ar['n_feasible']:raise ValueError(f'Feasibility mismatch: {rid}')
        is_local=not bool(higher)
        models={}; previous=None
        for p in (1,2,3):
            m=optimize(energy,feasible,p,starts,maxiter,seed+i*100+p,previous)
            models[f'p{p}']=m;previous=m['params']
            if is_local and export_qpy:
                # make_circuit expects separate gamma/beta arrays, unlike optimize's parameter vector
                circuit=make_circuit(energy,p,m['params'][:p],m['params'][p:],coeff)
                circuit.measure_all()
                circuit.name=f'{rid}_p{p}'
                circuits.append(circuit)
        winner=min((1,2,3),key=lambda p:models[f'p{p}']['expected_energy'])
        result={'record_id':rid,'stratum':row['stratum'],'exact_chain_local':is_local,
                'feasible_states':int(feasible.sum()),'n_nonlocal_z_terms':len(higher),
                'baseline_uniform_optimum_probability':len(get_optimal(energy,feasible))/N,
                'ideal_best_depth_by_expected_energy':winner,'models':models}
        records.append(result)
        for p in (1,2,3):
            m=models[f'p{p}'];table.append({'record_id':rid,'stratum':row['stratum'],
                'exact_chain_local':is_local,'p':p,'expected_energy':m['expected_energy'],
                'ideal_optimum_probability':m['ideal_optimum_probability'],
                'ideal_feasible_probability':m['ideal_feasible_probability'],
                'optimum_states':m['n_optimal_states']})
        print(f'{len(records):02d}/{limit} {rid} local={is_local}: '
              + ' '.join(f'p{p}={models[f"p{p}"]["ideal_optimum_probability"]:.1%}' for p in (1,2,3)),flush=True)
    summary={'version':'QHDE-v0.24','offline_only':True,'source_manifest_sha256':expected,
             'source_v23_audit_sha256':hashlib.sha256(audit.read_bytes()).hexdigest(),
             'seed':seed,'starts_random_per_depth':starts,'maxiter':maxiter,
             'objective':'MINIMIZE expected energy including infeasibility penalties; hit probability is evaluation only',
             'parameters':'[gamma_0..gamma_{p-1},beta_0..beta_{p-1}]',
             'n_records':len(records),'n_local':sum(r['exact_chain_local'] for r in records),
             'qpy_is_logical_not_transpiled':True,
             'qpu_submission':False,'records':records}
    (out/'optimization.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (out/'metrics.csv').open('w',encoding='utf-8',newline='') as f:
        if table:
            w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    if circuits:
        from qiskit import qpy
        with (out/'optimized_local_circuits.qpy').open('wb') as f:qpy.dump(circuits,f)
    print(f'SAVED {out}/optimization.json + metrics.csv; {len(circuits)} logical circuits; NO QPU JOB SUBMITTED')
    return summary


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',default=str(SRC));ap.add_argument('--audit',default=str(AUDIT))
    ap.add_argument('--out',default=str(OUT));ap.add_argument('--starts',type=int,default=12)
    ap.add_argument('--maxiter',type=int,default=200);ap.add_argument('--seed',type=int,default=42)
    ap.add_argument('--limit',type=int,default=16);ap.add_argument('--no-qpy',action='store_true')
    args=ap.parse_args()
    if args.starts<1 or args.maxiter<1 or args.limit<1:ap.error('starts/maxiter/limit must be positive')
    run(args.source,args.audit,args.out,args.starts,args.maxiter,args.seed,args.limit,not args.no_qpy)
if __name__=='__main__': main()
