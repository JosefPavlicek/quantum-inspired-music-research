"""QHDE v0.21: independently ordered, frozen-circuit IBM replication of v0.19.

Usage: --prepare (OFFLINE), --submit --confirm-spend-QPU (REAL QPU), --collect, --analyze.
Never submit twice. Does not modify the frozen QHDE v0.19 experiment.
"""
from __future__ import annotations
import argparse, hashlib, json, math, random
from datetime import datetime, timezone
from pathlib import Path

V19=Path('QHDE/results/ibm_v19')
OUT=Path('QHDE/results/replication_v21')
MODELS=('uniform','p1','p2','p3')

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def permutation(seed=20261028):
    a=list(range(64));random.Random(seed).shuffle(a);return a

def prepare(a):
    from qiskit import qpy
    if (a.out/'submitted_job.json').exists():raise RuntimeError('Existing submission — refusing to replace')
    prep=load(a.source/'preparation.json')
    if prep.get('version')!='QHDE-v0.19' or len(prep.get('circuit_names',[]))!=64 or len(prep['records'])!=16:
        raise ValueError('Expected frozen, 64-circuit QHDE v0.19 preparation')
    if prep['circuits_sha256']!=sha(a.source/'circuits.qpy') or prep['source_sha256']!=sha(prep['source_instances']):
        raise ValueError('v0.19 prepared artifacts have changed')
    with (a.source/'circuits.qpy').open('rb') as f:circuits=qpy.load(f)
    if [x.name for x in circuits]!=prep['circuit_names']:raise ValueError('Circuit order/name mismatch')
    # Same transpiled circuits, same calibration-sensitive gate content. Only randomized PUB ordering.
    perm=permutation(a.seed)
    a.out.mkdir(parents=True,exist_ok=True)
    with (a.out/'circuits.qpy').open('wb') as f:qpy.dump([circuits[i] for i in perm],f)
    snapshot={'version':'QHDE-v0.21','created_utc':now(),'parent_v19_job':'dbh5k4pt9uhs73c9h07g',
        'parent_preparation_sha256':sha(a.source/'preparation.json'),
        'parent_circuits_sha256':sha(a.source/'circuits.qpy'),
        'parent_analysis_sha256':sha(a.source/'analysis.json') if (a.source/'analysis.json').exists() else None,
        'backend':prep['backend'],'shots':prep['shots'],'seed':a.seed,
        'permutation_new_to_original':perm,
        'names_reordered':[prep['circuit_names'][i] for i in perm],
        'reordered_circuits_sha256':sha(a.out/'circuits.qpy'),
        'parent_source':str(a.source),
        'purpose':'Exact frozen-circuit replication with randomized execution order; no retuning or post-selection.',
        'qpu_jobs_submitted':0}
    save(a.out/'preparation.json',snapshot)
    print(f'PREPARED 64 frozen circuits, original backend {prep["backend"]}, shots={prep["shots"]}; NO QPU JOB')

def submit(a):
    if not a.confirm_spend_qpu:raise ValueError('Requires explicit --confirm-spend-QPU')
    if (a.out/'submitted_job.json').exists():raise RuntimeError('Already submitted; NEVER RESUBMIT')
    from qiskit import qpy
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    p=load(a.out/'preparation.json')
    if p['reordered_circuits_sha256']!=sha(a.out/'circuits.qpy') or p['parent_circuits_sha256']!=sha(a.source/'circuits.qpy'):
        raise ValueError('Frozen circuit files have changed')
    with (a.out/'circuits.qpy').open('rb') as f:circuits=qpy.load(f)
    if len(circuits)!=64 or [c.name for c in circuits]!=p['names_reordered']:raise ValueError('Circuit naming mismatch')
    service=QiskitRuntimeService(**({'instance':a.instance} if a.instance else {}))
    backend=service.backend(p['backend'])
    if not backend.status().operational:raise RuntimeError('Original backend is not operational; do not silently switch hardware')
    print('SUBMITTING 64 x',p['shots'],'on',p['backend'],'— QPU time will be charged')
    job=SamplerV2(mode=backend).run(circuits,shots=p['shots'])
    save(a.out/'submitted_job.json',{'job_id':job.job_id(),'backend':p['backend'],'circuits_sha256':p['reordered_circuits_sha256'], 'submitted_utc':now()})
    print('JOB ID',job.job_id(),'; DO NOT RESUBMIT')

def collect(a):
    from qiskit_ibm_runtime import QiskitRuntimeService
    job_data=load(a.out/'submitted_job.json'); p=load(a.out/'preparation.json')
    job=QiskitRuntimeService(**({'instance':a.instance} if a.instance else {})).job(job_data['job_id'])
    status=str(job.status());print('JOB',job_data['job_id'],'STATUS',status)
    if 'DONE' not in status.upper():return
    result=job.result()
    if len(result)!=64:raise ValueError('Unexpected number of result PUBs')
    ordered=[]
    for pub in result:
        reg=getattr(pub.data,'c',None)
        if reg is None:raise ValueError('Missing measurement register c')
        ordered.append({str(k):int(v) for k,v in reg.get_counts().items()})
    try:metrics=job.metrics()
    except Exception as e:metrics={'error':repr(e)}
    save(a.out/'raw_results.json',{'version':'QHDE-v0.21','job_id':job.job_id(),'status':status,
      'circuits_sha256':p['reordered_circuits_sha256'],'counts_reordered':ordered,'metrics':metrics})
    print('Saved raw_results.json; run --analyze')

def calculate(prep,raw,parent,prior):
    import numpy as np
    if raw['circuits_sha256']!=prep['reordered_circuits_sha256']:raise ValueError('Circuit manifest mismatch')
    if len(raw['counts_reordered'])!=64:raise ValueError('Expected 64 result distributions')
    if len(prep['permutation_new_to_original'])!=64 or sorted(prep['permutation_new_to_original'])!=list(range(64)):
        raise ValueError('Not a 64-circuit permutation')
    old_order=[None]*64
    for new,old in enumerate(prep['permutation_new_to_original']):old_order[old]=raw['counts_reordered'][new]
    rows=[]
    for i,p in enumerate(parent['records']):
        rid=p['record_id']; prior_rec=prior['records'][i]
        if rid!=prior_rec['record_id']:raise ValueError('Parent analysis record order differs')
        optimal=set(p['optimal_basis_indices']); scores=np.asarray(p['scores_16'],float)
        comparison=[]
        for j,model in enumerate(MODELS):
            counts=old_order[4*i+j];n=sum(counts.values())
            if n!=prep['shots']:raise ValueError('Shot mismatch')
            distribution=np.zeros(16); hits=0
            for bits,count in counts.items():
                index=int(bits.replace(' ',''),2)
                if index<0 or index>=16:raise ValueError('Unexpected basis index')
                distribution[index]+=count/n
                if index in optimal:hits+=count
            old=prior_rec['results'][j]
            if old['model']!=model:raise ValueError('Parent model order differs')
            comparison.append({'model':model,'replicate_hits':hits,'replicate_probability':hits/n,
                'original_probability':old['optimum_probability'],
                'replicate_expected_score':float(distribution@scores),
                'original_expected_score':old['expected_harmonic_score'],
                'difference_rep_minus_original':hits/n-old['optimum_probability'],
                'ideal_probability':old['ideal_optimum_probability']})
        rows.append({'record_id':rid,'stratum':p['stratum'],'n_optima':len(optimal),
                     'music_features':p['music_features'],'results':comparison})
    means={model:{key:float(np.mean([r['results'][j][key] for r in rows])) for key in
            ('replicate_probability','original_probability','difference_rep_minus_original')}
            for j,model in enumerate(MODELS)}
    winners={model:0 for model in MODELS[1:]}
    for r in rows:
        choice=max(r['results'][1:],key=lambda x:x['replicate_probability'])['model'];winners[choice]+=1
    return {'version':'QHDE-v0.21','job_id':raw.get('job_id'),'backend':prep['backend'],'means':means,
            'winner_counts':winners,'records':rows,'metrics':raw.get('metrics'),
            'cautions':['Second measurement is a replication, not a new independent musical task.',
                        'Single calibration epoch per job; shot-level uncertainty does not capture drift.',
                        'Only two melody segments and score-precomputed 16-state optimization.',
                        'No quantum advantage claim.']}

def analyze(a):
    prep=load(a.out/'preparation.json');raw=load(a.out/'raw_results.json')
    if prep['parent_preparation_sha256']!=sha(a.source/'preparation.json'):raise ValueError('Parent prep changed')
    if prep['parent_analysis_sha256']!=sha(a.source/'analysis.json'):raise ValueError('Parent analysis changed')
    report=calculate(prep,raw,load(a.source/'preparation.json'),load(a.source/'analysis.json'))
    save(a.out/'analysis.json',report)
    print('WINNERS',report['winner_counts'])
    for model,m in report['means'].items():
        print(model,'original',f'{m["original_probability"]:.2%}','replicated',f'{m["replicate_probability"]:.2%}',
              'delta',f'{m["difference_rep_minus_original"]:+.2%}')
    print('Saved',a.out/'analysis.json')

def main():
    ap=argparse.ArgumentParser(description=__doc__);g=ap.add_mutually_exclusive_group(required=True)
    for name in ('prepare','submit','collect','analyze'):g.add_argument('--'+name,action='store_true')
    ap.add_argument('--source',type=Path,default=V19);ap.add_argument('--out',type=Path,default=OUT)
    ap.add_argument('--seed',type=int,default=20261028);ap.add_argument('--instance')
    ap.add_argument('--confirm-spend-QPU',dest='confirm_spend_qpu',action='store_true')
    a=ap.parse_args()
    if a.prepare:prepare(a)
    elif a.submit:submit(a)
    elif a.collect:collect(a)
    else:analyze(a)
if __name__=='__main__':main()
