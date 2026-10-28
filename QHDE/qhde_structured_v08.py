"""QHDE v0.8: parity-Z/Walsh cost-Hamiltonian compression, offline only.

Use scores from HARMONIX corrected-candidate export. Do not access IBM hardware.
Index encoding is a_index*10 + b_index (not a_index*16+b_index).
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import DiagonalGate
from qiskit.quantum_info import Statevector

N=7
DIM=1 << N

def energies_from_export(data):
    pairs=data['pairs']
    if int(data['candidate_count'])!=10 or len(pairs)!=100:
        raise ValueError('Expected 10 corrected candidates, 100 admissible pairs')
    scores=np.full(DIM,np.nan)
    for row in pairs:
        i,j=int(row['a_index']),int(row['b_index'])
        if not (0<=i<10 and 0<=j<10): raise ValueError('Out of range candidate index')
        ix=10*i+j
        if np.isfinite(scores[ix]): raise ValueError('Duplicate pair index')
        scores[ix]=float(row['score'])
    if not np.isfinite(scores[:100]).all(): raise ValueError('Missing or nonfinite scores')
    lo,hi=float(scores[:100].min()),float(scores[:100].max())
    # Penalize invalid states by giving a lower score; magnitude is explicitly reported.
    invalid_score=lo-(hi-lo if hi>lo else 1.)
    scores[100:]=invalid_score
    # Minimization-energy convention: favorable chords have lower energy.
    energies=-scores
    return scores, energies, invalid_score

def walsh_coefficients(energies):
    """H= sum_mask coeff[mask] * product_{q in mask} Z_q.
    Qiskit little-endian: bit q corresponds to qubit q.
    """
    coeff=np.asarray(energies,dtype=float).copy()
    n=coeff.size
    if n != DIM: raise ValueError('Expected 128 energies')
    for stride in [1,2,4,8,16,32,64]:
        for start in range(0,n,2*stride):
            x=coeff[start:start+stride].copy()
            y=coeff[start+stride:start+2*stride].copy()
            coeff[start:start+stride]=x+y
            coeff[start+stride:start+2*stride]=x-y
    return coeff/n

def reconstruct(coeff):
    # Inverse Walsh, no 1/n after forward normalization.
    a=np.asarray(coeff,dtype=float).copy()
    for stride in [1,2,4,8,16,32,64]:
        for start in range(0,DIM,2*stride):
            x=a[start:start+stride].copy()
            y=a[start+stride:start+2*stride].copy()
            a[start:start+stride]=x+y
            a[start+stride:start+2*stride]=x-y
    return a

def select_coeffs(coeff, max_terms=None, max_degree=None):
    vals=np.asarray(coeff).copy()
    ranked=[i for i in range(1,DIM) if abs(vals[i])>1e-12 and (max_degree is None or i.bit_count()<=max_degree)]
    ranked.sort(key=lambda i:(-abs(vals[i]),i))
    kept=ranked if max_terms is None else ranked[:max_terms]
    selected=np.zeros(DIM)
    selected[0]=vals[0]   # global phase does not affect probabilities
    selected[kept]=vals[kept]
    return selected

def append_parity_phase(qc,mask,angle):
    """Implements exp(-i * angle * Z_mask); global phase omitted."""
    active=[q for q in range(N) if (mask>>q)&1]
    if not active: return
    target=active[-1]
    for q in active[:-1]:qc.cx(q,target)
    qc.rz(2*angle,target)
    for q in reversed(active[:-1]):qc.cx(q,target)

def cost_circuit(coeff,gamma):
    qc=QuantumCircuit(N)
    for mask in range(1,DIM):
        if abs(coeff[mask])>1e-12:
            append_parity_phase(qc,mask,gamma*float(coeff[mask]))
    return qc

def qaoa_circuit(coeff, gammas, betas):
    if len(gammas)!=len(betas) or not gammas:raise ValueError('Gammas and betas required')
    qc=QuantumCircuit(N)
    qc.h(range(N))
    for g,b in zip(gammas,betas):
        qc.compose(cost_circuit(coeff,g),inplace=True)
        for q in range(N):qc.rx(2*b,q)
    return qc

def reference_qaoa(energies,gammas,betas):
    qc=QuantumCircuit(N)
    qc.h(range(N))
    for g,b in zip(gammas,betas):
        qc.append(DiagonalGate(np.exp(-1j*g*np.asarray(energies))),list(range(N)))
        for q in range(N):qc.rx(2*b,q)
    return qc

def phase_aligned_error(a,b):
    phase=np.vdot(b,a)
    if abs(phase)>0: b=b*(phase/abs(phase))
    return float(np.max(np.abs(a-b)))

def audit(scores,energies,invalid_score,max_terms, max_degree, gamma, beta, level):
    coeff=walsh_coefficients(energies)
    selected=select_coeffs(coeff,max_terms,max_degree)
    approx=reconstruct(selected)
    original=Statevector.from_instruction(reference_qaoa(energies,[gamma],[beta])).data
    tested=Statevector.from_instruction(qaoa_circuit(selected,[gamma],[beta])).data
    # Note: compare amplitudes modulo global phase (constant Hamiltonian coefficient).
    err=phase_aligned_error(original,tested)
    physical=transpile(qaoa_circuit(selected,[gamma],[beta]),basis_gates=['rz','sx','x','cx'],optimization_level=level,seed_transpiler=42)
    counts={str(k):int(v) for k,v in physical.count_ops().items()}
    top_orig=set(np.flatnonzero(np.isclose(scores[:100],max(scores[:100]),rtol=0,atol=1e-9)).tolist())
    top_approx=set(np.flatnonzero(np.isclose(-approx[:100],max(-approx[:100]),rtol=0,atol=1e-9)).tolist())
    p=np.abs(tested)**2
    return {'max_terms':max_terms,'max_degree':max_degree,'kept_nonidentity_terms':int(np.count_nonzero(np.abs(selected[1:])>1e-12)),
            'max_energy_error_valid':float(np.max(abs(energies[:100]-approx[:100]))),
            'rmse_energy_valid':float(np.sqrt(np.mean((energies[:100]-approx[:100])**2))),
            'max_statevector_error_up_to_global_phase':err,
            'top_optimum_preserved':top_orig==top_approx,'optimal_overlap':len(top_orig&top_approx),
            'original_optima':sorted(top_orig),'approx_optima':sorted(top_approx),
            'p_original_optima':float(sum(p[list(top_orig)])),
            'p_invalid':float(sum(p[100:])),
            'depth':physical.depth(),'cx':counts.get('cx',0),'gates':int(sum(counts.values())),
            'ops':counts,'invalid_score':invalid_score}

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input-dir',default='QHDE/results/hooktheory_v04')
    ap.add_argument('--out',default='QHDE/results/structured_v08')
    ap.add_argument('--limit',type=int,default=5)
    ap.add_argument('--gamma',type=float,default=0.7)
    ap.add_argument('--beta',type=float,default=0.4)
    ap.add_argument('--level',type=int,choices=(0,1,2,3),default=1)
    args=ap.parse_args(argv)
    files=sorted(Path(args.input_dir).glob('scores_*.json'))[:args.limit]
    if not files:ap.error('No scores_*.json files found')
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    allrows=[]
    for file in files:
        data=json.loads(file.read_text(encoding='utf8'))
        scores,energies,invalid=energies_from_export(data)
        results=[]
        for name,k,degree in [('exact',None,None),('top16',16,None),('top32',32,None),('degree2',None,2)]:
            r=audit(scores,energies,invalid,k,degree,args.gamma,args.beta,args.level)
            r['variant']=name;results.append(r)
            print(f'{file.name} {name}: CX={r["cx"]}, depth={r["depth"]}, '
                  f'energy_RMSE={r["rmse_energy_valid"]:.6g}, '
                  f'preserve_optimum={r["top_optimum_preserved"]}, '
                  f'invalid={100*r["p_invalid"]:.2f}%')
        allrows.append({'file':file.name,'record_id':data.get('record_id'), 'results':results})
    path=out/'summary.json'
    path.write_text(json.dumps({'version':'QHDE-v0.8','simulation_only':True,'no_ibm_calls':True,
        'note':'Generic Walsh decomposition, not yet a physically local music-factor Hamiltonian. '
               'Fixed gamma,beta for equivalence/resource analysis, not optimized QAOA.',
        'records':allrows},indent=2),encoding='utf8')
    print('Saved',path)
if __name__=='__main__':main()
