"""QHDE v0.23: exact 8-qubit structured-cost circuit preparation (OFFLINE).

Reads v0.22 instances. Uses Walsh/Pauli-Z decomposition of full 256-entry
energy, including infeasibility penalties; does not silently truncate terms.
No IBM connection, no job submission. Circuit simulation validates all 256 basis
phases and a p=1 statevector against an independent numpy calculation.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np

DEFAULT_IN = Path('QHDE/results/four_segments_v22')
DEFAULT_OUT = Path('QHDE/results/structured_v23')
N = 8


def fwht(a):
    """Unnormalised Walsh-Hadamard transform; in-place butterfly on a copy."""
    a = np.asarray(a, float).copy()
    if a.shape != (256,): raise ValueError('Expected 256 energies')
    h = 1
    while h < 256:
        for i in range(0, 256, 2*h):
            x = a[i:i+h].copy(); y = a[i+h:i+2*h].copy()
            a[i:i+h] = x + y
            a[i+h:i+2*h] = x - y
        h *= 2
    return a


def walsh_coefficients(energy):
    a=np.asarray(energy,float)
    if a.shape!=(256,) or not np.all(np.isfinite(a)):
        raise ValueError('Invalid 8-qubit energies')
    return fwht(a)/256


def reconstruct(coeff): return fwht(coeff)


def support_properties(mask):
    bits=[i for i in range(N) if mask & (1<<i)]
    blocks={i//2 for i in bits}
    return len(bits), len(blocks), (max(blocks)-min(blocks) if blocks else 0)


def analyze(energy, tol=1e-10):
    c=walsh_coefficients(energy)
    nz=[(mask,float(coef)) for mask,coef in enumerate(c) if mask and abs(coef)>tol]
    higher=[(mask,coef) for mask,coef in nz if support_properties(mask)[1]>2 or support_properties(mask)[2]>1]
    rec=reconstruct(c)
    err=float(np.max(np.abs(rec-energy)))
    return c,nz,higher,err


def parity_phase(qc, mask, theta):
    """Implement exp(-i theta Z_mask) up to global phase."""
    bits=[i for i in range(N) if mask & (1<<i)]
    for a,b in zip(bits[:-1],bits[1:]): qc.cx(a,b)
    qc.rz(2*theta,bits[-1])
    for a,b in reversed(list(zip(bits[:-1],bits[1:]))): qc.cx(a,b)


def make_circuit(energy, p, gammas, betas, coeff=None, tol=1e-10):
    from qiskit import QuantumCircuit
    if len(gammas)!=p or len(betas)!=p: raise ValueError('Parameter count mismatch')
    coeff=walsh_coefficients(energy) if coeff is None else coeff
    qc=QuantumCircuit(N)
    qc.h(range(N))
    for depth in range(p):
        for mask in range(1,256):
            if abs(coeff[mask])>tol: parity_phase(qc,mask,float(gammas[depth])*float(coeff[mask]))
        for q in range(N): qc.rx(2*float(betas[depth]),q)
    return qc


def validate_qiskit(energy, coeff, tol=1e-10):
    """Validate phase oracle on each computational basis and p=1 probability."""
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector
    gamma=0.731; beta=0.414
    phase=QuantumCircuit(N)
    for mask in range(1,256):
        if abs(coeff[mask])>tol: parity_phase(phase,mask,gamma*float(coeff[mask]))
    # Global phase from identity coefficient is intentionally omitted.
    diagonal=np.diag(__import__('qiskit').quantum_info.Operator(phase).data)
    expected=np.exp(-1j*gamma*(np.asarray(energy)-coeff[0]))
    phase_error=float(np.max(np.abs(diagonal-expected)))
    if phase_error>1e-8: raise AssertionError(f'Basis phase mismatch {phase_error}')
    qc=make_circuit(energy,1,[gamma],[beta],coeff,tol)
    result=Statevector.from_instruction(qc).data
    # independent numpy mixer: qubit 0 is the least significant bit
    state=np.exp(-1j*gamma*np.asarray(energy))/16
    for q in range(N):
        step=1<<q
        updated=state.copy()
        for base in range(0,256,2*step):
            for j in range(step):
                i=base+j; k=i+step
                updated[i]=np.cos(beta)*state[i]-1j*np.sin(beta)*state[k]
                updated[k]=np.cos(beta)*state[k]-1j*np.sin(beta)*state[i]
        state=updated
    probability_error=float(np.max(np.abs(np.abs(state)**2-np.abs(result)**2)))
    if probability_error>1e-8: raise AssertionError(f'Statevector mismatch {probability_error}')
    return {'basis_phase_max_error':phase_error,'p1_probability_max_error':probability_error}


def run(source, out, limit=16, depths=(1,2,3), validate=True, tol=1e-10):
    source=Path(source);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    rows=[]; circuits=[]; names=[]
    qiskit_available=True
    try: import qiskit
    except ImportError: qiskit_available=False
    if not qiskit_available:
        print('Qiskit unavailable: energy decomposition and audit only; no QPY generated')
    for row in manifest['records'][:limit]:
        if row.get('status')!='ok': continue
        item=json.loads((source/row['file']).read_text(encoding='utf-8'))
        energy=np.asarray(item['energies_256'],float)
        coeff,nz,higher,error=analyze(energy,tol)
        if error>1e-9: raise AssertionError('Energy decomposition mismatch')
        feasible=sum(s is not None for s in item['scores_256'])
        metric={'record_id':row['record_id'],'stratum':row['stratum'],
                'source_file':row['file'],'n_feasible':feasible,
                'n_infeasible':256-feasible,'n_nonzero_z_terms':len(nz),
                'n_nonlocal_z_terms':len(higher),
                'max_z_order':max((support_properties(mask)[0] for mask,_ in nz),default=0),
                'energy_max_error':error,'exact_chain_local':len(higher)==0,
                'estimated_cx_per_cost_layer':sum(2*(support_properties(mask)[0]-1) for mask,_ in nz),
                'qiskit_validation':None,'circuits':{},
                'note':'Pauli-Z expansion exact. Dense or nonlocal terms are retained, not truncated.'}
        if qiskit_available:
            if validate:metric['qiskit_validation']=validate_qiskit(energy,coeff,tol)
            for p in depths:
                # Fixed deterministic probe parameters: NOT variationally optimized.
                gammas=[0.6+0.11*j for j in range(p)]
                betas=[0.35-0.04*j for j in range(p)]
                qc=make_circuit(energy,p,gammas,betas,coeff,tol)
                name=f'{row["record_id"]}_probe_p{p}'
                qc.name=name
                twoq=int(qc.count_ops().get('cx',0))
                metric['circuits'][f'p{p}']={'cx':twoq,'depth':qc.depth(),
                                          'gammas':gammas,'betas':betas}
                circuits.append(qc);names.append(name)
        rows.append(metric)
        print(f'{len(rows):02d} {row["record_id"]}: {len(nz)} Z terms, {len(higher)} nonlocal, ~{metric["estimated_cx_per_cost_layer"]} CX/cost')
    result={'version':'QHDE-v0.23','offline_only':True,'source_manifest_sha256':hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest(),
            'representation':'exact 8-qubit Pauli-Z/Walsh parity-gadget cost, no truncation',
            'probe_parameters_not_optimized':True,'qiskit_available':qiskit_available,
            'no_ibm_jobs_submitted':True,'records':rows}
    (out/'audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    if circuits:
        from qiskit import qpy
        with (out/'probe_circuits.qpy').open('wb') as f:qpy.dump(circuits,f)
    total=sum(v['estimated_cx_per_cost_layer'] for v in rows)
    print(f'OK {len(rows)} instances; total estimated CX per cost layer {total}; circuits {len(circuits)}; NO QPU JOBS')
    return result


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--source',default=str(DEFAULT_IN));a.add_argument('--out',default=str(DEFAULT_OUT))
    a.add_argument('--limit',type=int,default=16)
    a.add_argument('--no-qiskit-validation',action='store_true')
    args=a.parse_args();run(args.source,args.out,args.limit,validate=not args.no_qiskit_validation)
if __name__=='__main__':main()
