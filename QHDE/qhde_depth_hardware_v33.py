#!/usr/bin/env python3
"""QHDE v0.33: fixed research question, prespecified 24-task IBM depth replication.
No QPU execution without --submit --confirm-spend-QPU.
Requires existing QHDE/qhde_ibm_v25.py, qhde_optimize_v24.py,
qhde_structured_qaoa_v23.py. Run from repository root.
"""
import argparse,csv,hashlib,io,json,collections,math
from pathlib import Path
import numpy as np
from qhde_ibm_v25 import check_map,TWOQ,sha,save,load,utc,simulate,get_optimal,decompose,make_circuit,wilson

LABELS=('uniform','p1','p2','p3')

def choose(manifest,metrics,n_per_stratum=6):
    """Selection blind to QAOA outcomes; training only, 256 feasible, distinct landscapes.
    Within stratum, take quantiles of *input* chord entropy, then deterministic ID tie-break.
    """
    by=collections.defaultdict(list); used=set()
    for r in manifest['records']:
        if r['status']!='ok' or r['partition']!='internal_train' or r['n_feasible']!=256:continue
        h=r['landscape_hash']
        if h in used:continue
        used.add(h);by[r['stratum']].append(r)
    result=[]
    if len(by)!=4:raise ValueError('Expected exactly four reference-music strata')
    for stratum,rows in sorted(by.items()):
        rows.sort(key=lambda r:(r['chord_entropy_bits'],r['record_id']))
        if len(rows)<n_per_stratum:raise ValueError('Insufficient entries '+stratum)
        ix=np.linspace(0,len(rows)-1,n_per_stratum).round().astype(int)
        result.extend(rows[int(i)] for i in ix)
    if len({r['landscape_hash'] for r in result})!=len(result):raise ValueError('Duplicate landscapes selected')
    return result

def read_runs(path):
    path=Path(path)
    if not path.is_file():raise FileNotFoundError(f'Missing optimization results: {path}')
    with path.open(encoding='utf-8') as f:
        runs=[json.loads(line) for line in f if line.strip()]
    ids=[r['record_id'] for r in runs]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate run record IDs')
    return {r['record_id']:r for r in runs}

def read_sources(instances_dir, results_dir):
    inst=Path(instances_dir);results=Path(results_dir)
    manifest_path=inst/'manifest.json'
    if not manifest_path.is_file():raise FileNotFoundError(f'Missing manifest: {manifest_path}')
    if not (results/'runs.jsonl').is_file():raise FileNotFoundError(f'Missing runs: {results / "runs.jsonl"}')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    return inst,manifest,read_runs(results/'runs.jsonl')

def source_checksums(instances_dir, results_dir):
    inst=Path(instances_dir);results=Path(results_dir)
    return {'manifest_sha256':sha(inst/'manifest.json'),
            'runs_sha256':sha(results/'runs.jsonl'),
            'metrics_sha256':sha(results/'metrics.csv') if (results/'metrics.csv').is_file() else None}

def build(a):
    from qiskit import QuantumCircuit,ClassicalRegister
    from qiskit.quantum_info import Statevector
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService
    from qiskit import qpy
    out=Path(a.out)
    if (out/'preparation.json').exists():raise FileExistsError('Preparation exists; never overwrite')
    inst,manifest,runs=read_sources(a.instances_dir,a.results_dir)
    entries=choose(manifest,None,a.per_stratum)
    logical=[]; recs=[]
    for i,r in enumerate(entries):
        rid=r['record_id'];data=json.loads((inst/r['file']).read_text(encoding='utf-8')); opt_run=runs[rid]
        if opt_run['landscape_hash']!=r['landscape_hash']:raise ValueError('Landscape mismatch: '+rid)
        energy=np.array(data['energies_256'],float)
        feasible=np.array([x is not None for x in data['scores_256']],bool)
        if not feasible.all():raise ValueError('Selected restricted case')
        coeff,terms,higher,err=decompose(energy)
        if err>1e-9 or higher:raise ValueError('Selected case is not exact chain-local: '+rid)
        opt=np.asarray(get_optimal(energy,feasible),int)
        expected={}
        for label in LABELS:
            p=0 if label=='uniform' else int(label[1:]);name=f'q33_{i:02d}_{label}'
            if p==0:
                q=QuantumCircuit(8);q.h(range(8)); dist=np.ones(256)/256
            else:
                m=opt_run['models'][label];params=np.asarray(m['params'],float)
                if len(params)!=2*p:raise ValueError('Bad params')
                dist=simulate(energy,params,p)
                if abs(float(dist[opt].sum())-float(m['ideal_optimum_probability']))>1e-8:raise ValueError('Simulation mismatch')
                q=make_circuit(energy,p,params[:p],params[p:],coeff)
            if np.max(np.abs(np.abs(Statevector.from_instruction(q).data)**2-dist))>1e-8:raise ValueError('Circuit mismatch')
            expected[label]={'optimum_probability':float(dist[opt].sum()),'expected_energy':float(dist@energy)}
            q.add_register(ClassicalRegister(8,'c'));q.measure(range(8),range(8));q.name=name;logical.append(q)
        recs.append({'id':rid,'stratum':r['stratum'],'landscape_hash':r['landscape_hash'],
          'source_file':r['file'],'opt_indices':opt.tolist(),'energies':energy.tolist(),
          'n_optimal':len(opt),'expected':expected,
          'chord_entropy_bits':r['chord_entropy_bits'],
          'conditional_transition_entropy_bits':r['conditional_transition_entropy_bits'],
          'repeated_bigram_rate':r['repeated_bigram_rate']})
    # Repetitions are independent PUBs in one job and are not independent backend calibrations.
    service=QiskitRuntimeService(**({'instance':a.instance} if a.instance else {}))
    choices=[]
    for backend_name in a.backends:
        try:
            backend=service.backend(backend_name)
            if not backend.status().operational:continue
            pm=generate_preset_pass_manager(backend=backend,optimization_level=a.level,seed_transpiler=a.seed,approximation_degree=1.0)
            circuits=[];stats=[]
            for rep in range(a.repeats):
                for q in logical:
                    t=pm.run(q);t.name=f'{q.name}_r{rep}'
                    bad=set(t.count_ops())-set(backend.target.operation_names)-{'barrier','delay'}
                    if bad:raise ValueError('Unsupported ops: '+str(bad))
                    mapping=check_map(t)
                    cnt=t.count_ops();two=sum(int(v) for k,v in cnt.items() if k in TWOQ)
                    circuits.append(t);stats.append({'name':t.name,'two_qubit_gates':two,'depth':t.depth(),'map':mapping})
            twoq=sum(x['two_qubit_gates'] for x in stats)
            queue=int(backend.status().pending_jobs)
            print(f'{backend_name}: {len(circuits)} circuits; two-qubit gates={twoq}; queue={queue}; max depth={max(x["depth"] for x in stats)}',flush=True)
            choices.append((twoq,queue,backend_name,circuits,stats))
        except Exception as e:print(f'Cannot prepare {backend_name}: {e}',flush=True)
    if not choices:raise RuntimeError('No viable quantum backend')
    twoq,queue,backend_name,circuits,stats=min(choices,key=lambda x:(x[0],x[1]))
    out.mkdir(parents=True,exist_ok=True)
    with (out/'circuits.qpy').open('wb') as f:qpy.dump(circuits,f)
    save(out/'preparation.json',{'version':'QHDE-v0.33','backend':backend_name,'queue':queue,'shots':a.shots,
      'repeats':a.repeats,'n_records':len(recs),'n_circuits':len(circuits),
      'source_checksums':source_checksums(a.instances_dir,a.results_dir),
      'circuits_sha256':sha(out/'circuits.qpy'),'names':[c.name for c in circuits],
      'selection':'TRAIN-only, six entropy quantiles per predeclared HookTheory stratum; no QAOA outcomes for selection',
      'records':recs,'transpiled':stats,'two_qubit_gates':twoq,'prepared_utc':utc()})
    print(f'PREPARED {len(recs)} tasks, {len(circuits)} circuits on {backend_name}, {a.shots} shots each. NO QPU USED.',flush=True)
    print('Inspect preparation.json and estimated IBM job charge before submitting.',flush=True)

def submit(a):
    if not a.confirm_spend_qpu:raise ValueError('Explicit --confirm-spend-QPU required')
    from qiskit_ibm_runtime import QiskitRuntimeService,SamplerV2
    from qiskit import qpy
    out=Path(a.out)
    if (out/'submitted_job.json').exists() or (out/'submission_attempt.json').exists():raise FileExistsError('Submission already attempted; inspect IBM Jobs before retry')
    p=load(out/'preparation.json')
    if a.shots!=p['shots'] or sha(out/'circuits.qpy')!=p['circuits_sha256']:raise ValueError('Input changed')
    if source_checksums(a.instances_dir,a.results_dir)!=p['source_checksums']:raise ValueError('Source changed')
    with (out/'circuits.qpy').open('rb') as f:circuits=qpy.load(f)
    if len(circuits)!=p['n_circuits'] or [c.name for c in circuits]!=p['names']:raise ValueError('Circuit list changed')
    service=QiskitRuntimeService(**({'instance':a.instance} if a.instance else {}))
    backend=service.backend(p['backend'])
    if not backend.status().operational:raise ValueError('Backend unavailable')
    # Pre-create submit lock to avoid accidental duplicate submissions after uncertain network error.
    save(out/'submission_attempt.json',{'time':utc(),'backend':p['backend'],'circuits_sha256':p['circuits_sha256']})
    print('SUBMITTING',len(circuits),'circuits; actual IBM charge not guaranteed',flush=True)
    job=SamplerV2(mode=backend).run(circuits,shots=a.shots)
    save(out/'submitted_job.json',{'job_id':job.job_id(),'backend':p['backend'],'circuits_sha256':p['circuits_sha256'],'submitted_utc':utc()})
    print('JOB ID',job.job_id(),flush=True)

def collect(a):
    from qiskit_ibm_runtime import QiskitRuntimeService
    out=Path(a.out);p=load(out/'preparation.json');s=load(out/'submitted_job.json')
    job=QiskitRuntimeService(**({'instance':a.instance} if a.instance else {})).job(s['job_id'])
    status=str(job.status());print('JOB',s['job_id'],'STATUS',status,flush=True)
    if 'DONE' not in status.upper():return
    res=job.result()
    if len(res)!=p['n_circuits']:raise ValueError('Wrong result count')
    counts=[{str(k):int(v) for k,v in pub.data.c.get_counts().items()} for pub in res]
    save(out/'raw_results.json',{'job_id':s['job_id'],'status':status,'circuits_sha256':p['circuits_sha256'],
        'names':p['names'],'counts':counts,'metrics':job.metrics(),'retrieved_utc':utc()})
    print('Saved raw_results.json',flush=True)

def analyze(a):
    out=Path(a.out);p=load(out/'preparation.json');raw=load(out/'raw_results.json')
    if raw['circuits_sha256']!=p['circuits_sha256'] or raw['names']!=p['names']:raise ValueError('Result/preparation mismatch')
    rows=[];meta=[];n=len(p['records']);nr=p['repeats']
    for i,r in enumerate(p['records']):
        for li,label in enumerate(LABELS):
            hits=0;shots=0;en=0.0;opts=set(r['opt_indices']);envec=np.asarray(r['energies'],float)
            for rep in range(nr):
                counts=raw['counts'][rep*n*4 + i*4 +li]
                sh=sum(counts.values())
                if sh!=p['shots']:raise ValueError('Shots mismatch')
                for bit,k in counts.items():
                    idx=int(bit.replace(' ',''),2)
                    if idx>=256:raise ValueError('Bad bitstring')
                    hits+=k if idx in opts else 0;en+=k*envec[idx]
                shots+=sh
            pp=hits/shots;ideal=r['expected'][label]['optimum_probability']
            rows.append({'record_id':r['id'],'stratum':r['stratum'],'model':label,'hardware_optimum_probability':pp,
               'ideal_optimum_probability':ideal,'noise_gap_pp':100*(ideal-pp),
               'hardware_expected_energy':en/shots,'ideal_expected_energy':r['expected'][label]['expected_energy'],
               'shots':shots,'hits':hits,'wilson_95':wilson(hits,shots),
               'conditional_transition_entropy_bits':r['conditional_transition_entropy_bits']})
    means={m:{k:float(np.mean([x[k] for x in rows if x['model']==m])) for k in ['hardware_optimum_probability','ideal_optimum_probability','noise_gap_pp']} for m in LABELS}
    import scipy.stats as stats
    piv={rid:{x['model']:x for x in rows if x['record_id']==rid} for rid in {x['record_id'] for x in rows}}
    gains=np.array([piv[r['id']]['p3']['hardware_optimum_probability']-piv[r['id']]['p2']['hardware_optimum_probability'] for r in p['records']])
    ent=np.array([r['conditional_transition_entropy_bits'] for r in p['records']])
    rho,pval=stats.spearmanr(ent,gains)
    report={'version':'QHDE-v0.33','job_id':raw['job_id'],'backend':p['backend'],'n_records':n,
       'shots_per_model':nr*p['shots'],'means':means,
       'p3_minus_p2_mean_pp':float(100*np.mean(gains)),
       'p3_minus_p2_positive':int(np.count_nonzero(gains>0)),
       'p3_minus_p2_negative':int(np.count_nonzero(gains<0)),
       'p3_minus_p2_ties':int(np.count_nonzero(gains==0)),
       'exploratory_music_entropy_vs_hardware_gain_spearman':{'rho':float(rho),'p_uncorrected':float(pval)},
       'qpu_metrics':raw['metrics'],
       'notes':['Hardware-selected set comes from TRAIN, not a held-out test.','Two repetitions within one job do not establish separate calibration replication.','Same energy models and parameters as v0.30, model-scored optimum.','No quantum advantage; classical DP beats quantum for unconstrained four-chord chains.']}
    save(out/'analysis.json',report)
    with (out/'per_model.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    txt=['# QHDE v0.33 – prespecified hardware depth test',f'Job: {raw["job_id"]}; backend: {p["backend"]}; tasks: {n}; shots/model: {nr*p["shots"]}.','', '|Model|Ideal optimum (%)|Hardware optimum (%)|Gap (pp)|','|---|---:|---:|---:|']
    for m in LABELS:txt.append(f'|{m}|{100*means[m]["ideal_optimum_probability"]:.2f}|{100*means[m]["hardware_optimum_probability"]:.2f}|{means[m]["noise_gap_pp"]:.2f}|')
    txt += ['',f'Mean hardware benefit p3–p2: {report["p3_minus_p2_mean_pp"]:.2f} pp; +/−/tie = {report["p3_minus_p2_positive"]}/{report["p3_minus_p2_negative"]}/{report["p3_minus_p2_ties"]}.',f'Exploratory whole-song transition entropy vs hardware gain: rho={rho:.3f}, p={pval:.4f}.','', '*No quantum advantage claim; task-selection and music-annotation caveats remain.*']
    (out/'REPORT.md').write_text('\n'.join(txt)+'\n')
    print('\n'.join(txt),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group()
    for m in ('prepare','submit','collect','analyze'):g.add_argument('--'+m,action='store_true')
    p.add_argument('--instances-dir',default='QHDE/results/expanded_v29_full')
    p.add_argument('--results-dir',default='QHDE/results/optimize_v30_full')
    p.add_argument('--out',default='QHDE/results/hardware_v33')
    p.add_argument('--shots',type=int,default=2048);p.add_argument('--repeats',type=int,default=2)
    p.add_argument('--per-stratum',type=int,default=6)
    p.add_argument('--backends',nargs='+',default=['ibm_marrakesh','ibm_pittsburgh'])
    p.add_argument('--instance');p.add_argument('--seed',type=int,default=42);p.add_argument('--level',type=int,default=2,choices=[0,1,2,3])
    p.add_argument('--confirm-spend-QPU',action='store_true',dest='confirm_spend_qpu')
    a=p.parse_args()
    if a.shots<1 or a.shots>10000 or a.repeats<1 or a.repeats>5 or a.per_stratum<1 or a.per_stratum>20:p.error('Invalid budget')
    if a.submit:submit(a)
    elif a.collect:collect(a)
    elif a.analyze:analyze(a)
    else:build(a)
if __name__=='__main__':main()
