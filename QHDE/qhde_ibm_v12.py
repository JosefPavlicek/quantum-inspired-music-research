"""QHDE v0.12: hardware calibration audit, QPY preparation and explicit opt-in Sampler submission.

Run from repository root. Default action PREPARE only. NEVER submit without --submit
and --confirm-spend-QPU. The command does not print or serialize credentials.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import numpy as np


SCORES = 'QHDE/results/hooktheory_v04/scores_000.json'
SUMMARY = 'QHDE/results/hardware_v10/summary.json'
OUT = 'QHDE/results/ibm_v12'
TWO_Q = {'cx','cz','ecr','iswap','rzz','swap','rxx','ryy','rzx'}


def source_problem(scores_path, summary_path, p):
    from qhde_hardware_v10 import build_problem, make_circuit
    source = json.loads(Path(scores_path).read_text(encoding='utf-8'))
    report = json.loads(Path(summary_path).read_text(encoding='utf-8'))
    problem = build_problem(source)
    item = next((r for r in report['records'] if Path(r['score_file']).name == Path(scores_path).name), None)
    if item is None:
        raise ValueError('No matching optimized parameter row in v0.10 summary')
    params = np.asarray(item['models'][f'p{p}']['params'], dtype=float)
    if len(params) != 2*p: raise ValueError('Incorrect parameter vector')
    probabilities = np.abs(__import__('qhde_hardware_v10').np_state(problem['energies'], params))**2
    qc = make_circuit(problem['energies'], params, measure=True)
    # Explicitly name output register so the result can be recovered robustly.
    qc.name = f'QHDE_p{p}'
    uniform = make_uniform()
    optimal = np.isclose(problem['subscores'].reshape(16), problem['subset_optimum'], rtol=0, atol=1e-10)
    return qc, uniform, {
        'source_record_id': source.get('record_id'),
        'full_optimum_represented': bool(problem['full_optimum_represented']),
        'subset_optimum': float(problem['subset_optimum']),
        'a_indices': [int(x) for x in problem['a_indices']],
        'b_indices': [int(x) for x in problem['b_indices']],
        'optimal_basis_indices': [int(x) for x in np.where(optimal)[0]],
        'p':p, 'qaoa_params': params.tolist(),
        'ideal_qaoa_optimum_probability': float(np.sum(probabilities[optimal])),
        'ideal_uniform_optimum_probability': float(np.mean(optimal)),
    }


def make_uniform():
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(4,4, name='uniform_control')
    qc.h(range(4)); qc.measure(range(4),range(4))
    return qc


def gate_properties(backend, qubits):
    target=backend.target
    rows=[]
    for q in qubits:
        prop=target.qubit_properties[q] if target.qubit_properties else None
        meas=target['measure'].get((q,)) if 'measure' in target.operation_names else None
        rows.append({'qubit':int(q), 't1_s':getattr(prop,'t1',None),
                     't2_s':getattr(prop,'t2',None),
                     'readout_error':getattr(meas,'error',None)})
    return rows


def two_qubit_details(circ, backend):
    from collections import Counter
    counts=Counter(); log_success=0.0; missing=0
    for instruction in circ.data:
        name=instruction.operation.name
        if name not in TWO_Q: continue
        q=tuple(circ.find_bit(x).index for x in instruction.qubits)
        counts[name]+=1
        # Record calibrated gate error as an engineering diagnostic only.
        props=backend.target[name].get(q) if name in backend.target.operation_names else None
        err=getattr(props,'error',None)
        if err is None: missing+=1
        elif 0 <= err < 1: log_success += float(np.log1p(-err))
        else: missing+=1
    return {'two_qubit_count':sum(counts.values()), 'two_qubit_by_gate':dict(counts),
            'two_qubit_error_metadata_missing':missing,
            'product_of_2q_gate_fidelities_partial':float(np.exp(log_success))}


def compile_for(backend, circuits, p, seed=42, level=2):
    from qiskit.transpiler import generate_preset_pass_manager
    pm=generate_preset_pass_manager(backend=backend, optimization_level=level,
                                    seed_transpiler=seed, approximation_degree=1.0)
    compiled=[pm.run(c) for c in circuits]
    for qc in compiled:
        if qc.num_clbits != 4: raise ValueError('Unexpected classical bit count')
        if set(qc.count_ops()) & {'diagonal','unitary'}:
            raise ValueError('Circuit still has nonnative instructions')
        unsupported=set(qc.count_ops()) - set(backend.target.operation_names) - {'barrier'}
        if unsupported: raise ValueError(f'Unsupported operations: {unsupported}')
    out=[]
    for qc in compiled:
        props=two_qubit_details(qc,backend)
        out.append({'name':qc.name,'depth':qc.depth(),'size':qc.size(),
                    'operations':{str(k):int(v) for k,v in qc.count_ops().items()},**props})
    return compiled,out


def preparation(args):
    from qiskit_ibm_runtime import QiskitRuntimeService
    from qiskit import qpy
    service=QiskitRuntimeService(**({'instance':args.instance} if args.instance else {}))
    qc,uniform,problem=source_problem(args.scores,args.summary,args.p)
    candidates=[]
    for name in args.backends:
        backend=service.backend(name)
        if not backend.status().operational: continue
        compiled,metrics=compile_for(backend,[uniform,qc],args.p,args.seed,args.level)
        status=backend.status()
        candidates.append((sum(m['two_qubit_count'] for m in metrics),name,backend,compiled,metrics,
                           int(getattr(status,'pending_jobs',0))))
        print(f'{name}: uniform 2q={metrics[0]["two_qubit_count"]}, '
              f'QAOA p={args.p} 2q={metrics[1]["two_qubit_count"]}, depth={metrics[1]["depth"]}')
    if not candidates: raise ValueError('No operational backend available')
    candidates.sort(key=lambda r:(r[0],r[5],r[1]))
    _,name,backend,circuits,metrics,queue=candidates[0]
    directory=Path(args.out);directory.mkdir(parents=True,exist_ok=True)
    with (directory/'prepared_circuits.qpy').open('wb') as f:qpy.dump(circuits,f)
    # Extract physical qubits involved in any nontrivial gate or measurement.
    used=sorted({qc.find_bit(q).index for qc in circuits for inst in qc.data
                 if inst.operation.name not in {'barrier','delay'} for q in inst.qubits})
    report={'version':'QHDE-v0.12','created_utc':datetime.now(timezone.utc).isoformat(),
            'backend':name,'backend_pending_jobs_at_preparation':queue,
            'seed_transpiler':args.seed,'optimization_level':args.level,
            'shots_proposed':args.shots,'circuits_order':['uniform','qaoa'],
            'score_file':args.scores,'summary_file':args.summary,
            'problem':problem,'transpiled':metrics,
            'physical_qubits_used':used,'qubit_properties':gate_properties(backend,used),
            'qpy_file':'prepared_circuits.qpy','qpu_jobs_submitted':0,
            'warning':'Topology and calibration reflect metadata at preparation time. No runtime is guaranteed. Candidate reduction uses model scores and changes original 100-pair problem.'}
    (directory/'preparation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(f'SELECTED: {name} (total 2q={sum(m["two_qubit_count"] for m in metrics)}, queue={queue})')
    print('Saved',directory/'preparation.json','and prepared_circuits.qpy. NO QPU JOBS SUBMITTED.')


def submit(args):
    if not args.confirm_spend_qpu:
        raise ValueError('QPU submission requires BOTH --submit and --confirm-spend-QPU')
    from qiskit import qpy
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    directory=Path(args.out)
    report=json.loads((directory/'preparation.json').read_text())
    if args.backends and report['backend'] not in args.backends:
        raise ValueError('Prepared backend differs from requested backend')
    if args.shots != report['shots_proposed']:
        raise ValueError('Shot count differs from prepared manifest; reprepare first')
    with (directory/'prepared_circuits.qpy').open('rb') as f:circuits=qpy.load(f)
    if len(circuits)!=2: raise ValueError('Expected uniform and QAOA circuits')
    service=QiskitRuntimeService(**({'instance':args.instance} if args.instance else {}))
    backend=service.backend(report['backend'])
    if not backend.status().operational: raise ValueError('Backend offline')
    sampler=SamplerV2(mode=backend)
    # THE ONLY LINE IN THIS PACKAGE THAT SUBMITS REAL QPU WORK.
    job=sampler.run(circuits,shots=args.shots)
    job_id=job.job_id()
    output={'job_id':job_id,'backend':report['backend'],'shots':args.shots,
            'circuits_order':report['circuits_order'],
            'submitted_utc':datetime.now(timezone.utc).isoformat(),
            'status':'submitted','qpu_cost_unknown':True}
    (directory/'submitted_job.json').write_text(json.dumps(output,indent=2)+'\n')
    print('QPU job submitted:',job_id)
    print('Job ID saved to',directory/'submitted_job.json')
    print('Use --collect to retrieve results; do not resubmit accidentally.')


def collect(args):
    from qiskit_ibm_runtime import QiskitRuntimeService
    directory=Path(args.out)
    info=json.loads((directory/'submitted_job.json').read_text())
    service=QiskitRuntimeService(**({'instance':args.instance} if args.instance else {}))
    job=service.job(info['job_id'])
    print('Job:',info['job_id'],'status:',job.status())
    result=job.result()
    datasets=[]
    for pub in result:
        # Classical register defaults to 'c' for 4-bit circuits.
        data=getattr(pub.data,'c',None)
        if data is None: raise ValueError('Missing expected classical register c')
        datasets.append({str(k):int(v) for k,v in data.get_counts().items()})
    report={'job_id':info['job_id'],'backend':info['backend'],'shots':info['shots'],
            'uniform_counts':datasets[0],'qaoa_counts':datasets[1]}
    prep=json.loads((directory/'preparation.json').read_text())
    opt=set(prep['problem']['optimal_basis_indices'])
    for label,counts in [('uniform',datasets[0]),('qaoa',datasets[1])]:
        n=sum(counts.values());hits=sum(v for bits,v in counts.items() if int(bits.replace(' ',''),2) in opt)
        report[label+'_optimum_probability']=hits/n if n else None
    (directory/'measured_results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Measured optimum probabilities:',report['uniform_optimum_probability'],report['qaoa_optimum_probability'])
    print('Saved',directory/'measured_results.json')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    actions=ap.add_mutually_exclusive_group()
    actions.add_argument('--submit',action='store_true',help='EXPLICIT opt-in real QPU submission')
    actions.add_argument('--collect',action='store_true',help='Collect previously submitted job')
    ap.add_argument('--confirm-spend-QPU',dest='confirm_spend_qpu',action='store_true')
    ap.add_argument('--backends',nargs='+',default=['ibm_pittsburgh','ibm_marrakesh'])
    ap.add_argument('--instance',default=None,help='Optional instance identifier, not an API key')
    ap.add_argument('--p',type=int,choices=[1,2],default=1)
    ap.add_argument('--scores',default=SCORES)
    ap.add_argument('--summary',default=SUMMARY)
    ap.add_argument('--out',default=OUT)
    ap.add_argument('--shots',type=int,default=1024)
    ap.add_argument('--seed',type=int,default=42)
    ap.add_argument('--level',type=int,choices=[0,1,2,3],default=2)
    args=ap.parse_args()
    if not 1 <= args.shots <= 10000: ap.error('Shots must be between 1 and 10000')
    if args.collect:collect(args)
    elif args.submit:submit(args)
    else:preparation(args)

if __name__=='__main__':main()
