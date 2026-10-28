"""QHDE v0.14: deterministic, OFFLINE audit of stored IBM v0.12/v0.13 runs.

Run from repository root: HARMONIX/.venv/bin/python QHDE/qhde_audit_v14.py
No IBM credentials, network, QPU, or write to source data are used.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from pathlib import Path
import numpy as np

OUT = Path('QHDE/results/audit_v14')
V13 = Path('QHDE/results/ibm_v13')
V12 = Path('QHDE/results/ibm_v12')

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p, data):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
def wilson(k,n,z=1.959963984540054):
    if n <= 0: raise ValueError('Shots must be positive')
    p=k/n; den=1+z*z/n
    middle=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0.,middle-half), min(1.,middle+half)]
def parse_counts(counts):
    result=np.zeros(16,dtype=np.int64)
    for bits, count in counts.items():
        clean=bits.replace(' ','')
        if len(clean)!=4 or any(c not in '01' for c in clean):
            raise ValueError(f'Unexpected 4-bit outcome: {bits!r}')
        if not isinstance(count,int) or count<0:raise ValueError('Invalid counts')
        result[int(clean,2)] += count
    if not result.sum():raise ValueError('Empty counts')
    return result

def subset_from_source(record):
    # Import the same v0.10 scorer that generated the submitted QAOA circuits.
    from qhde_hardware_v10 import build_problem
    source=read(record['score_file'])
    problem=build_problem(source)
    if source.get('record_id') != record['record_id']:
        raise ValueError('Record identifier mismatch')
    if problem['a_indices'] != record['problem']['a_indices'] or problem['b_indices'] != record['problem']['b_indices']:
        raise ValueError('Candidate index mapping changed')
    if bool(problem['full_optimum_represented']) != bool(record['problem']['full_optimum_represented']):
        raise ValueError('Full optimum representation mismatch')
    subs=np.asarray(problem['subscores']).reshape(16)
    opt=np.where(np.isclose(subs, max(subs),rtol=0,atol=1e-10))[0].tolist()
    if opt != record['problem']['optimal_basis_indices']:
        raise ValueError('Optimal basis indices do not match reconstructed scores')
    return subs,problem

def measured_row(counts, scores, optimal, model, ideal_opt, ideal_dist=None):
    n=int(counts.sum()); p=counts/n; mask=np.zeros(16,dtype=bool);mask[optimal]=True
    k=int(counts[mask].sum()); mean=float(p@scores)
    variance=float(p@(scores-mean)**2)
    result={'model':model,'shots':n,'optimal_hits':k,'optimal_probability':k/n,
            'optimal_wilson_95':wilson(k,n),'ideal_optimal_probability':float(ideal_opt),
            'ideal_gap_percentage_points':100*(k/n-float(ideal_opt)),
            'expected_harmonic_score':mean,'score_sem':math.sqrt(variance/n),
            'score_mean_normal_95':[mean-1.959964*math.sqrt(variance/n),mean+1.959964*math.sqrt(variance/n)]}
    if ideal_dist is not None:
        result['total_variation_distance_from_ideal']=float(np.sum(np.abs(p-ideal_dist))/2)
    return result

def delta(a,b):
    # Independent circuit samples. Normal CI is exploratory; no unmeasured systematic errors included.
    x=a['optimal_probability'];y=b['optimal_probability'];n=a['shots'];m=b['shots']
    se=math.sqrt(x*(1-x)/n+y*(1-y)/m)
    d=y-x
    return {'delta_percentage_points':100*d,
            'normal_95_percentage_points':[100*(d-1.959964*se),100*(d+1.959964*se)],
            'standard_error_percentage_points':100*se}

def classical_baselines(scores,opt):
    n=len(scores); m=len(opt)
    out={'exact_enumeration':{'candidate_evaluations':n,'optimum_score':float(max(scores)),
                              'guarantees_optimum':True},
         'single_uniform_draw_optimum_probability':m/n,
         'random_with_replacement':[]}
    ordered=np.sort(scores)
    for k in [1,2,4,8,16,32,64,128,1024]:
        # E[max of k independent draws] via CDF of discrete ordered scores.
        vals,counts=np.unique(ordered,return_counts=True)
        cdf=np.cumsum(counts)/n
        weights=np.diff(np.concatenate(([0.0],cdf**k)))
        out['random_with_replacement'].append({'draws':k,
            'probability_at_least_one_optimum':1-(1-m/n)**k,
            'expected_best_score':float(np.dot(weights,vals))})
    return out

def audit(v13=V13,v12=V12,out=OUT):
    v13=Path(v13);out=Path(out)
    prep=read(v13/'preparation.json');raw=read(v13/'raw_results.json')
    if prep['version']!='QHDE-v0.13':raise ValueError('Unexpected manifest version')
    if raw['job_id'] != read(v13/'submitted_job.json')['job_id']:
        raise ValueError('Submitted job does not match raw results')
    names=prep['circuits_order']
    if names!=raw['circuits_order'] or len(names)!=15 or len(raw['counts_ordered'])!=15:
        raise ValueError('Counts/circuit order mismatch')
    if len(prep['records'])!=5:raise ValueError('Expected five records')
    if sha(prep['source_summary']) != prep['source_summary_sha256']:
        raise ValueError('v0.10 summary changed since QPU preparation')
    summary=read(prep['source_summary']);summary_by_file={Path(r['score_file']).name:r for r in summary['records']}
    rows=[]
    for i,rec in enumerate(prep['records']):
        if sha(rec['score_file'])!=rec['score_sha256']:
            raise ValueError(f'Score source changed: {rec["score_file"]}')
        scores,problem=subset_from_source(rec)
        opt=rec['problem']['optimal_basis_indices']
        models=summary_by_file[Path(rec['score_file']).name]['models']
        results=[]
        for j,label in enumerate(['uniform','p1','p2']):
            counts=parse_counts(raw['counts_ordered'][3*i+j])
            if counts.sum()!=prep['shots']:raise ValueError('Shot count mismatch')
            dist=(np.full(16,1/16) if label=='uniform' else np.asarray(models[label]['probabilities'],dtype=float))
            if len(dist)!=16 or not np.isclose(dist.sum(),1,atol=1e-8):raise ValueError('Invalid ideal distribution')
            ideal=(rec['problem']['ideal_uniform_optimum_probability'] if label=='uniform' else rec[label]['ideal_optimum_probability'])
            if not np.isclose(dist[opt].sum(),ideal,atol=1e-8):raise ValueError('Model probability inconsistency')
            row=measured_row(counts,scores,opt,label,ideal,dist)
            row['ideal_expected_harmonic_score']=float(dist@scores)
            results.append(row)
        rows.append({'record_id':rec['record_id'],'score_file':rec['score_file'],
            'num_tied_optima':len(opt),'full_optimum_represented':problem['full_optimum_represented'],
            'optimal_basis_indices':opt,'scores_16':scores.tolist(),
            'results':results,
            'p1_minus_uniform':delta(results[0],results[1]),
            'p2_minus_uniform':delta(results[0],results[2]),
            'p2_minus_p1':delta(results[1],results[2]),
            'classical_baselines':classical_baselines(scores,opt)})
    doc={'version':'QHDE-v0.14','offline_only':True,'submitted_jobs':0,
         'job_id':raw['job_id'],'backend':raw['backend'],
         'original_metrics':raw.get('metrics'),
         'important_limits':['Only five selected TRAIN records; one job per circuit; results share calibration conditions.',
          'Four-by-four model-selected subset, not the full 100-pair problem.',
          'Optimum is defined by corrected EMH model scores, not human harmony.',
          'Classical exhaustive search finds the optimum with just 16 score evaluations; no quantum advantage claim.',
          'Count-to-basis mapping is assumed from Qiskit measure(q[i], c[i]); verify layout and measurement map separately before publication.',
          'Binomial intervals do not account for calibration drift or correlated hardware errors.',
          'QAOA parameters were optimized classically; their optimization cost is excluded from the QPU shots.'],
         'records':rows}
    if (Path(v12)/'measured_results.json').exists():
        old=read(Path(v12)/'measured_results.json')
        doc['v12_pilot']={'job_id':old.get('job_id'),'backend':old.get('backend'),
             'uniform_probability':old.get('uniform_optimum_probability'),
             'qaoa_probability':old.get('qaoa_optimum_probability'),
             'note':'Different backend/date; do not pool with v0.13 as independent repeats.'}
    dump(out/'audit.json',doc)
    with (out/'metrics.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['record_id','model','shots','optimal_hits','optimum_probability','wilson_lo','wilson_hi','mean_score','score_sem','ideal_optimum_probability','tvd'])
        for r in rows:
            for x in r['results']:
                w.writerow([r['record_id'],x['model'],x['shots'],x['optimal_hits'],x['optimal_probability'],*x['optimal_wilson_95'],x['expected_harmonic_score'],x['score_sem'],x['ideal_optimal_probability'],x['total_variation_distance_from_ideal']])
    lines=['# QHDE v0.14 — Offline experimental audit','',f'IBM job: `{raw["job_id"]}` / `{raw["backend"]}`','',
           '| Record | Uniform | p=1 | p=2 | Δ p2–p1 (pp; approx. 95% CI) |','|---|---:|---:|---:|---:|']
    for r in rows:
        x=r['results'];d=r['p2_minus_p1'];ci=d['normal_95_percentage_points']
        lines.append(f'| {r["record_id"]} | {x[0]["optimal_probability"]:.2%} | {x[1]["optimal_probability"]:.2%} | {x[2]["optimal_probability"]:.2%} | {d["delta_percentage_points"]:+.2f} [{ci[0]:+.2f}, {ci[1]:+.2f}] |')
    lines += ['','## Interpretation','',
       'These are model-score optima in a preselected 16-state problem, not a test of quantum advantage.',
       'Exact classical enumeration requires 16 score evaluations per record; random-search comparisons are analytical.',
       'Intervals summarize per-circuit shot noise only. Independent runs are needed to assess drift.',
       'The recorded bit ordering follows the original Qiskit measurement convention and requires a separate transpilation-layout audit.',
       'Source score and model summary SHA-256 values were verified against the preparation manifest.','']
    (out/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print('\n'.join(lines[:len(rows)+5]));print('Saved',out/'audit.json',out/'metrics.csv',out/'REPORT.md')
    return doc

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--v13',default=str(V13));ap.add_argument('--v12',default=str(V12));ap.add_argument('--out',default=str(OUT))
    a=ap.parse_args();audit(a.v13,a.v12,a.out)
if __name__=='__main__':main()
