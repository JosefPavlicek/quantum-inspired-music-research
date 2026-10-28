"""QHDE v0.19 — 16 independent HookTheory instances, QAOA p=1/2/3 on IBM QPU.

Prepare is the default and never submits. All jobs need --submit --confirm-spend-QPU.
Only the 4x4 fixed-candidate, two-segment task is investigated. No speedup claim.
Run from repository root using HARMONIX/.venv/bin/python.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np

BASE=Path('QHDE/results/ibm_v19')
SOURCE=Path('QHDE/results/construct_v18/instances.json')
TWOQ={'cx','cz','ecr','iswap','rzz','swap','rxx','ryy','rzx'}

def utc(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, d):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical_energy(scores):
    s=np.asarray(scores,dtype=float)
    if s.shape!=(16,) or not np.isfinite(s).all():raise ValueError('Expected exactly 16 finite scores')
    span=float(np.ptp(s))
    if span<1e-12:raise ValueError('Degenerate score landscape')
    return -(s-float(np.min(s)))/span

def make_circuit(energy, params=None, name='', measure=True):
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import DiagonalGate
    energy=np.asarray(energy,dtype=float)
    if energy.shape!=(16,) or not np.isfinite(energy).all():raise ValueError('Bad energies')
    qc=QuantumCircuit(4,4,name=name) if measure else QuantumCircuit(4,name=name)
    qc.h(range(4))
    if params is not None:
        params=np.asarray(params,dtype=float)
        if len(params) not in (2,4,6) or not np.isfinite(params).all():raise ValueError('Expected p=1..3 parameters')
        for k in range(0,len(params),2):
            gamma,beta=params[k:k+2]
            qc.append(DiagonalGate(np.exp(-1j*gamma*energy).tolist()),range(4))
            qc.rx(2*float(beta),range(4))
    if measure:qc.measure(range(4),range(4))
    return qc

def validate_instance(row, atol=1e-8):
    from qiskit.quantum_info import Statevector
    from qhde_hardware_v10 import np_state
    if row.get('status')!='ok':raise ValueError('Non-OK record')
    reduction=row['reduction']; scores=np.asarray(reduction['scores_16'])
    energy=canonical_energy(scores)
    optimal=np.flatnonzero(np.isclose(scores,max(scores),rtol=0,atol=1e-10)).tolist()
    if optimal!=reduction['optimal_basis_indices']:raise ValueError('Optimum index mismatch')
    models={}
    for p in (1,2,3):
        data=row['models'][f'p{p}']; params=np.asarray(data['params'],dtype=float)
        if params.shape!=(2*p,):raise ValueError('Wrong optimizer parameter count')
        ideal=np.abs(np_state(energy,params))**2
        qiskit=np.abs(Statevector.from_instruction(make_circuit(energy,params,measure=False)).data)**2
        err=float(np.max(np.abs(ideal-qiskit)))
        if err>atol:raise ValueError(f'Qiskit/NumPy mismatch p={p}, {err}')
        if abs(float(ideal[optimal].sum())-data['ideal_optimum_probability'])>atol:
            raise ValueError(f'Stored ideal optimum probability mismatch p={p}')
        if abs(float(ideal@scores)-data['ideal_expected_score'])>atol:
            raise ValueError(f'Stored expected score mismatch p={p}')
        models[f'p{p}']={'params':params.tolist(),'ideal_optimal_probability':float(ideal[optimal].sum()),
                         'ideal_expected_score':float(ideal@scores),'max_probability_error':err}
    return energy, optimal, models

def check_measurements(c):
    """Verify transpiler final layout and measurement map preserve logical bit order.

    This is essential: int('c3c2c1c0',2) must equal the pre-transpile basis index.
    Refuse to submit if layout metadata is unavailable or ambiguous.
    """
    layout=getattr(c,'layout',None)
    if layout is None:raise ValueError(f'{c.name}: no final layout metadata')
    try: mapping=layout.final_index_layout(filter_ancillas=True)
    except Exception as e:raise ValueError(f'{c.name}: cannot identify logical-to-physical mapping') from e
    if len(mapping)!=4 or len(set(mapping))!=4:raise ValueError(f'{c.name}: invalid final layout {mapping}')
    measured={}
    for inst in c.data:
        if inst.operation.name!='measure':continue
        if len(inst.qubits)!=1 or len(inst.clbits)!=1:raise ValueError('Unexpected measurement structure')
        physical=c.find_bit(inst.qubits[0]).index
        classical=c.find_bit(inst.clbits[0]).index
        if physical in measured:raise ValueError('Duplicate measurement of physical qubit')
        measured[physical]=classical
    for logical,physical in enumerate(mapping):
        if measured.get(physical)!=logical:
            raise ValueError(f'{c.name}: logical q{logical} -> physical {physical} -> classical '
                             f'{measured.get(physical)}, not c{logical}')
    if len(measured)!=4 or c.num_clbits!=4:raise ValueError('Unexpected number of measurements/classical bits')
    return {'logical_to_physical':list(map(int,mapping)), 'mapping_verified':True}

def build_raw(src):
    rows=src.get('records',[])
    if src.get('version')!='QHDE-v0.18' or src.get('split')!='TRAIN' or len(rows)!=16:
        raise ValueError('Expected exactly 16 frozen TRAIN instances from QHDE v0.18')
    all_circuits=[];manifest=[];ids=set()
    for i,row in enumerate(rows):
        rid=row['record_id']
        if rid in ids:raise ValueError('Duplicate record ID')
        ids.add(rid)
        if row.get('reduction',{}).get('a_indices')!=[0,2,4,6] or row['reduction'].get('b_indices')!=[0,2,4,6]:
            raise ValueError('Unexpected reduction policy')
        energy, opt, models=validate_instance(row)
        names=[f'clip_{i:02d}_uniform']+[f'clip_{i:02d}_p{p}' for p in (1,2,3)]
        all_circuits.append(make_circuit(energy,None,names[0]))
        for p in (1,2,3):all_circuits.append(make_circuit(energy,models[f'p{p}']['params'],names[p]))
        manifest.append({'record_id':rid,'stratum':row['stratum'],'music_features':row.get('music_features',{}),
          'full_optimum_represented':row['reduction']['full_optimum_represented'],
          'optimal_basis_indices':opt,'scores_16':row['reduction']['scores_16'],
          'uniform_optimal_probability':len(opt)/16,'models':models,'names':names})
    return all_circuits,manifest

def compile_backend(backend,raw,seed,level):
    from qiskit.transpiler import generate_preset_pass_manager
    pm=generate_preset_pass_manager(backend=backend,seed_transpiler=seed,
                                    optimization_level=level,approximation_degree=1.0)
    compiled=[];stats=[]
    for rawqc in raw:
        qc=pm.run(rawqc)
        unsupported=set(qc.count_ops())-set(backend.target.operation_names)-{'barrier','delay'}
        if unsupported:raise ValueError(f'{qc.name}: unsupported operations {unsupported}')
        mapping=check_measurements(qc)
        gates={str(k):int(v) for k,v in qc.count_ops().items()}
        twoq=sum(v for k,v in gates.items() if k in TWOQ)
        compiled.append(qc)
        stats.append({'name':qc.name,'depth':int(qc.depth()),'size':int(qc.size()),'two_qubit_gates':twoq,
                      'operations':gates,**mapping})
    return compiled,stats

def prepare(a):
    from qiskit_ibm_runtime import QiskitRuntimeService
    from qiskit import qpy
    out=Path(a.out)
    if (out/'submitted_job.json').exists():raise ValueError('Job exists: refusing overwrite')
    src=load(a.instances);raw,records=build_raw(src)
    service=QiskitRuntimeService(**({'instance':a.instance} if a.instance else {}))
    candidates=[]
    for name in a.backends:
        b=service.backend(name)
        if not b.status().operational:continue
        qc,stats=compile_backend(b,raw,a.seed,a.level)
        gate_count=sum(s['two_qubit_gates'] for s in stats)
        queue=int(b.status().pending_jobs)
        candidates.append((gate_count,queue,name,qc,stats))
        print(f'{name}: {len(qc)} circuits, 2q total={gate_count}, deepest={max(x["depth"] for x in stats)}, queue={queue}')
    if not candidates:raise ValueError('No operational / compilable backend')
    candidates.sort(key=lambda item:item[:3])
    gates,queue,name,qc,stats=candidates[0]
    out.mkdir(parents=True,exist_ok=True)
    with (out/'circuits.qpy').open('wb') as fh:qpy.dump(qc,fh)
    report={'version':'QHDE-v0.19','created_utc':utc(),'backend':name,'queue':queue,
            'source_instances':str(a.instances),'source_sha256':sha(a.instances),
            'shots':a.shots,'seed_transpiler':a.seed,'optimization_level':a.level,
            'circuit_names':[c.name for c in qc],'circuits_sha256':sha(out/'circuits.qpy'),
            'records':records,'transpiled':stats,'total_2q_gates':gates,
            'warning':'16 TRAIN clips, fixed four candidates per segment, first TWO segments only; no quantum advantage claim.',
            'qpu_jobs_submitted':0}
    save(out/'preparation.json',report)
    print('SELECTED',name,'; saved preparation.json + circuits.qpy ; NO JOBS SUBMITTED')

def submit(a):
    if not a.confirm_spend_qpu:raise ValueError('Both --submit and --confirm-spend-QPU required')
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    from qiskit import qpy
    out=Path(a.out)
    if (out/'submitted_job.json').exists():raise ValueError('Already submitted. DO NOT RESUBMIT')
    prep=load(out/'preparation.json')
    if sha(prep['source_instances'])!=prep['source_sha256'] or sha(out/'circuits.qpy')!=prep['circuits_sha256']:
        raise ValueError('Frozen experiment content changed')
    if a.shots!=prep['shots']:raise ValueError('Shots differ from preparation')
    with (out/'circuits.qpy').open('rb') as fh:circuits=qpy.load(fh)
    if len(circuits)!=64 or [c.name for c in circuits]!=prep['circuit_names']:
        raise ValueError('Circuit count/order mismatch')
    service=QiskitRuntimeService(**({'instance':a.instance} if a.instance else {}))
    backend=service.backend(prep['backend'])
    if not backend.status().operational:raise ValueError('Backend offline')
    print(f'SUBMITTING 64 circuits x {a.shots} shots on {backend.name}; QPU charge UNKNOWN')
    job=SamplerV2(mode=backend).run(circuits,shots=a.shots)
    save(out/'submitted_job.json',{'job_id':job.job_id(),'backend':prep['backend'],
         'shots':a.shots,'submitted_utc':utc(),'circuits_sha256':prep['circuits_sha256'],
         'circuit_names':prep['circuit_names']})
    print('JOB ID',job.job_id(),'— use --collect; NEVER repeat --submit')

def collect(a):
    from qiskit_ibm_runtime import QiskitRuntimeService
    out=Path(a.out);info=load(out/'submitted_job.json')
    job=QiskitRuntimeService(**({'instance':a.instance} if a.instance else {})).job(info['job_id'])
    status=str(job.status());print('JOB',job.job_id(),'STATUS',status)
    if 'DONE' not in status.upper():return
    res=job.result()
    if len(res)!=64:raise ValueError('Unexpected number of result PUBs')
    counts=[]
    for pub in res:
        c=getattr(pub.data,'c',None)
        if c is None:raise ValueError('Missing expected c classical register')
        counts.append({str(k):int(v) for k,v in c.get_counts().items()})
    try:metrics=job.metrics()
    except Exception as err:metrics={'error':str(err)}
    save(out/'raw_results.json',{'job_id':job.job_id(),'status':status,'metrics':metrics,
             'circuits_sha256':info['circuits_sha256'],'circuit_names':info['circuit_names'],
             'counts_ordered':counts,'retrieved_utc':utc()})
    print('Saved raw_results.json; run --analyze')

def wilson(k,n,z=1.96):
    p=k/n; d=1+z*z/n;ctr=(p+z*z/(2*n))/d
    r=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0,ctr-r),min(1,ctr+r)]

def analyze(a):
    out=Path(a.out);prep=load(out/'preparation.json');raw=load(out/'raw_results.json')
    if raw['circuit_names']!=prep['circuit_names'] or raw['circuits_sha256']!=prep['circuits_sha256']:
        raise ValueError('Manifest mismatch')
    if len(raw['counts_ordered'])!=64:raise ValueError('Unexpected PUB count')
    report=[]
    for i,row in enumerate(prep['records']):
        optimal=set(row['optimal_basis_indices']); scores=np.asarray(row['scores_16'],float)
        measurements=[]
        for j,label in enumerate(('uniform','p1','p2','p3')):
            counts=raw['counts_ordered'][4*i+j]
            n=sum(counts.values()); dist=np.zeros(16)
            if n!=prep['shots']:raise ValueError(f'Shot mismatch {i}/{label}: {n}')
            for bits,count in counts.items():
                idx=int(bits.replace(' ',''),2)
                if idx<0 or idx>=16:raise ValueError('Unexpected bit string')
                dist[idx]+=count/n
            hits=sum(count for bits,count in counts.items() if int(bits.replace(' ',''),2) in optimal)
            ideal=row['uniform_optimal_probability'] if label=='uniform' else row['models'][label]['ideal_optimal_probability']
            measurements.append({'model':label,'shots':n,'optimum_hits':hits,'optimum_probability':hits/n,
               'wilson_95':wilson(hits,n),'expected_harmonic_score':float(dist@scores),
               'ideal_optimum_probability':ideal,'state_probabilities':dist.tolist()})
        report.append({'record_id':row['record_id'],'stratum':row['stratum'],
          'music_features':row['music_features'],'full_optimum_represented':row['full_optimum_represented'],
          'n_optimal_states':len(optimal),'results':measurements})
    save(out/'analysis.json',{'version':'QHDE-v0.19','job_id':raw['job_id'],
         'backend':prep['backend'],'metrics':raw['metrics'],'records':report,
         'warning':'Single QPU job, 16 TRAIN clips, model-score optimum only; classical exact enumeration trivial.'})
    print('record / stratum | uniform | p1 | p2 | p3')
    for r in report:
        print(r['record_id'],r['stratum'],*(f'{x["optimum_probability"]:.2%}' for x in r['results']))
    print('Saved',out/'analysis.json')

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    actions=ap.add_mutually_exclusive_group()
    for name in ('prepare','submit','collect','analyze'):
        actions.add_argument('--'+name,action='store_true')
    ap.add_argument('--confirm-spend-QPU',action='store_true',dest='confirm_spend_qpu')
    ap.add_argument('--instances',default=str(SOURCE));ap.add_argument('--out',default=str(BASE))
    ap.add_argument('--backends',nargs='+',default=['ibm_marrakesh','ibm_pittsburgh'])
    ap.add_argument('--instance')
    ap.add_argument('--shots',type=int,default=1024)
    ap.add_argument('--seed',type=int,default=42)
    ap.add_argument('--level',type=int,choices=(0,1,2,3),default=2)
    a=ap.parse_args(argv)
    if not (1<=a.shots<=10000):ap.error('--shots must be 1..10000')
    if a.submit:submit(a)
    elif a.collect:collect(a)
    elif a.analyze:analyze(a)
    else:prepare(a)
if __name__=='__main__':main()
