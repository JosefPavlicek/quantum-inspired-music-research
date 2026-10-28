"""QHDE v0.13. Five-record, 4-qubit IBM pilot. PREPARE by default; no QPU spend.

Commands (repository root):
 python QHDE/qhde_ibm_v13.py --prepare
 python QHDE/qhde_ibm_v13.py --submit --confirm-spend-QPU
 python QHDE/qhde_ibm_v13.py --collect
 python QHDE/qhde_ibm_v13.py --analyze

The 15 circuits are sent together in ONE IBM job. No automatic re-submission.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import numpy as np

from qhde_ibm_v12 import compile_for, make_uniform, source_problem

ROOT = Path('QHDE/results')
DEFAULT_OUT = ROOT / 'ibm_v13'
TWOQ = {'cx','cz','ecr','iswap','rzz','swap','rxx','ryy','rzx'}

def utc(): return datetime.now(timezone.utc).isoformat()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path, obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def wilson(hits,n,z=1.96):
    if not n:return [None,None]
    p=hits/n;d=1+z*z/n
    mid=(p+z*z/(2*n))/d
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0,mid-half),min(1,mid+half)]

def problem_set(args):
    files=sorted(Path(args.scores_dir).glob('scores_*.json'))
    if len(files)!=5: raise ValueError(f'Expected exactly five score files, found {len(files)}')
    circuits=[]; manifest=[]
    for fp in files:
        uniform=make_uniform()
        uniform.name=f'{fp.stem}_uniform'
        circuits.append(uniform)
        row={'score_file':str(fp),'score_sha256':sha(fp),'circuits':[], 'record_id':None}
        for p in (1,2):
            qc,_,pr=source_problem(str(fp),args.summary,p)
            qc.name=f'{fp.stem}_p{p}'
            row['record_id']=pr['source_record_id']
            if p==1:
                row['problem']={k:pr[k] for k in ['a_indices','b_indices','full_optimum_represented','subset_optimum','optimal_basis_indices','ideal_uniform_optimum_probability']}
            row[f'p{p}']={'qaoa_params':pr['qaoa_params'],'ideal_optimum_probability':pr['ideal_qaoa_optimum_probability']}
            circuits.append(qc)
        manifest.append(row)
    return circuits,manifest

def prepare(args):
    from qiskit_ibm_runtime import QiskitRuntimeService
    from qiskit import qpy
    out=Path(args.out)
    if (out/'submitted_job.json').exists():
        raise ValueError('Existing submitted job in output folder: refusing to overwrite its preparation')
    raw,records=problem_set(args)
    service=QiskitRuntimeService(**({'instance':args.instance} if args.instance else {}))
    candidates=[]
    for name in args.backends:
        backend=service.backend(name)
        if not backend.status().operational:continue
        compiled, metrics=compile_for(backend,raw,1,args.seed,args.level)
        cost=sum(r['two_qubit_count'] for r in metrics)
        queue=int(backend.status().pending_jobs)
        candidates.append((cost,queue,name,compiled,metrics))
        print(f'{name}: 15 circuits; 2q gates total={cost}; queue={queue}')
    if not candidates:raise ValueError('No operational backend')
    candidates.sort(key=lambda c:(c[0],c[1],c[2]))
    cost,queue,name,compiled,metrics=candidates[0]
    out.mkdir(parents=True,exist_ok=True)
    with (out/'circuits.qpy').open('wb') as f:qpy.dump(compiled,f)
    if len(compiled)!=15 or any(c.num_clbits!=4 for c in compiled):raise ValueError('Unexpected circuit dimensions')
    report={'version':'QHDE-v0.13','created_utc':utc(),'backend':name,'queue_at_preparation':queue,
            'shots':args.shots,'seed_transpiler':args.seed,'optimization_level':args.level,
            'source_summary':args.summary,'source_summary_sha256':sha(args.summary),
            'records':records,'circuits_order':[c.name for c in compiled],
            'transpiled':metrics,'total_2q_gates':cost,'qpy_file':'circuits.qpy',
            'limitation':'5 TRAIN tasks, 16/100 selected pairs, same source of model scores, no reference harmony, no quantum speedup claim'}
    write(out/'preparation.json',report)
    print('SELECTED',name,'; saved preparation.json + circuits.qpy; NO QPU JOB SUBMITTED')

def submit(args):
    if not args.confirm_spend_qpu: raise ValueError('Explicit --confirm-spend-QPU required')
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    from qiskit import qpy
    out=Path(args.out)
    if (out/'submitted_job.json').exists():raise ValueError('Job already submitted; use --collect, never resubmit')
    prep=read(out/'preparation.json')
    if prep['shots'] != args.shots:raise ValueError('Shots differ from prepared manifest')
    if sha(prep['source_summary']) != prep['source_summary_sha256']:raise ValueError('Summary changed since preparation')
    for r in prep['records']:
        if sha(r['score_file']) != r['score_sha256']:raise ValueError('Score file changed since preparation')
    with (out/'circuits.qpy').open('rb') as f:circuits=qpy.load(f)
    if len(circuits)!=15 or [c.name for c in circuits]!=prep['circuits_order']:
        raise ValueError('Circuit content/name ordering differs from preparation')
    service=QiskitRuntimeService(**({'instance':args.instance} if args.instance else {}))
    backend=service.backend(prep['backend'])
    if not backend.status().operational:raise ValueError('Backend not operational')
    print(f'Submitting 15 circuits x {args.shots} shots to {prep["backend"]}; IBM QPU charge is unknown.')
    job=SamplerV2(mode=backend).run(circuits,shots=args.shots)
    write(out/'submitted_job.json',{'job_id':job.job_id(),'backend':prep['backend'],'submitted_utc':utc(),
                                    'shots':args.shots,'circuits_order':prep['circuits_order']})
    print('JOB ID',job.job_id(),'; use --collect; DO NOT RESUBMIT')

def collect(args):
    from qiskit_ibm_runtime import QiskitRuntimeService
    out=Path(args.out);sub=read(out/'submitted_job.json')
    job=QiskitRuntimeService(**({'instance':args.instance} if args.instance else {})).job(sub['job_id'])
    status=str(job.status());print('JOB',job.job_id(),'STATUS',status)
    if 'DONE' not in status.upper():
        print('Not complete; no result requested. Retry --collect later.');return
    result=job.result()
    if len(result)!=15:raise ValueError(f'Expected 15 circuit results, got {len(result)}')
    counts=[]
    for pub in result:
        reg=getattr(pub.data,'c',None)
        if reg is None:raise ValueError('Classical register c missing')
        counts.append({str(k):int(v) for k,v in reg.get_counts().items()})
    try:metrics=job.metrics()
    except Exception as ex:metrics={'unavailable':str(ex)}
    write(out/'raw_results.json',{'job_id':job.job_id(),'backend':sub['backend'],
                                   'retrieved_utc':utc(),'status':status,'metrics':metrics,
                                   'counts_ordered':counts,'circuits_order':sub['circuits_order']})
    print('Saved raw_results.json; run --analyze')

def analyze(args):
    out=Path(args.out);prep=read(out/'preparation.json');raw=read(out/'raw_results.json')
    if raw['circuits_order']!=prep['circuits_order']:raise ValueError('Circuit order mismatch')
    rows=[]
    for i,r in enumerate(prep['records']):
        opt=set(r['problem']['optimal_basis_indices']);entries=[]
        for j,label in enumerate(('uniform','p1','p2')):
            counts=raw['counts_ordered'][3*i+j]
            n=sum(counts.values())
            if n != prep['shots']:raise ValueError(f'Shots mismatch {i} {label}: {n}')
            hits=sum(v for s,v in counts.items() if int(s.replace(' ',''),2) in opt)
            entries.append({'label':label,'hits':hits,'shots':n,'probability':hits/n,
                            'wilson_95':wilson(hits,n),'ideal_probability':
                            r['problem']['ideal_uniform_optimum_probability'] if label=='uniform' else r[label]['ideal_optimum_probability']})
        rows.append({'score_file':r['score_file'],'record_id':r['record_id'],
                     'full_optimum_represented':r['problem']['full_optimum_represented'],
                     'num_tied_optima':len(opt),'optimal_basis_indices':sorted(opt),
                     'measurements':entries,
                     'qaoa_vs_uniform_p1_delta':entries[1]['probability']-entries[0]['probability'],
                     'qaoa_vs_uniform_p2_delta':entries[2]['probability']-entries[0]['probability']})
    write(out/'analysis.json',{'version':'QHDE-v0.13','job_id':raw['job_id'],'backend':raw['backend'],
                               'metrics':raw.get('metrics'),'records':rows,
                               'interpretation_note':'Wilson intervals are per-binomial estimates; repeated independent jobs are needed for calibration drift and robustness. No quantum advantage inferred.'})
    print('Record | uniform | QAOA p1 | QAOA p2 | tied')
    for row in rows:
        x=row['measurements'];print(row['record_id'],*('%.2f%%'%(v['probability']*100) for v in x),row['num_tied_optima'])
    print('Saved',out/'analysis.json')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    actions=ap.add_mutually_exclusive_group()
    actions.add_argument('--prepare',action='store_true')
    actions.add_argument('--submit',action='store_true')
    actions.add_argument('--collect',action='store_true')
    actions.add_argument('--analyze',action='store_true')
    ap.add_argument('--confirm-spend-QPU',action='store_true',dest='confirm_spend_qpu')
    ap.add_argument('--backends',nargs='+',default=['ibm_marrakesh','ibm_pittsburgh'])
    ap.add_argument('--instance')
    ap.add_argument('--scores-dir',default=str(ROOT/'hooktheory_v04'))
    ap.add_argument('--summary',default=str(ROOT/'hardware_v10'/'summary.json'))
    ap.add_argument('--out',default=str(DEFAULT_OUT))
    ap.add_argument('--shots',type=int,default=1024)
    ap.add_argument('--seed',type=int,default=42)
    ap.add_argument('--level',type=int,choices=(0,1,2,3),default=2)
    a=ap.parse_args()
    if not 1<=a.shots<=10000:ap.error('Shots must be 1..10000')
    if a.submit:submit(a)
    elif a.collect:collect(a)
    elif a.analyze:analyze(a)
    else:prepare(a)
if __name__=='__main__':main()
