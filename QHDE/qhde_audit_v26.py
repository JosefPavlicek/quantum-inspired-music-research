"""QHDE v0.26: fully offline, reproducible hardware/ideal gap analysis.

Uses actual v0.25 per-record probabilities; joins v0.23 circuit properties.
No IBM credentials, no Qiskit, no QPU submission.
"""
import argparse,csv,json,math,hashlib
from pathlib import Path
from itertools import product
import numpy as np

MODELS=('uniform','p1','p2','p3')

def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def mean(x): return float(np.mean(np.asarray(x,float)))
def spearman(x,y):
    from scipy.stats import spearmanr
    x=np.asarray(x,float);y=np.asarray(y,float)
    if len(x)<3 or np.std(x)<1e-12 or np.std(y)<1e-12: return None
    v=float(spearmanr(x,y).statistic)
    return v if math.isfinite(v) else None

def paired_test(d):
    """Exact two-sided sign-flip randomization, unit of analysis = music instance."""
    d=np.asarray(d,float);n=len(d);obs=abs(float(d.mean()))
    if n>20: raise ValueError('Exact paired test capped at 20 records')
    dist=np.fromiter((abs(float(np.mean(d*np.array(sign)))) for sign in product((-1.,1.),repeat=n)),dtype=float,count=2**n)
    return float(np.mean(dist>=obs-1e-12))

def ci_bootstrap(d,seed=2026,reps=10000):
    d=np.asarray(d,float)
    rng=np.random.default_rng(seed); ix=rng.integers(0,len(d),size=(reps,len(d)))
    return [float(v) for v in np.quantile(d[ix].mean(axis=1),[.025,.975])]

def run(analysis, audit=None, optimization=None, output='QHDE/results/audit_v26'):
    a=read(analysis)
    if a.get('version')!='QHDE-v0.25': raise ValueError('v0.25 analysis required')
    old={r['record_id']:r for r in read(audit)['records']} if audit and Path(audit).exists() else {}
    opt={r['record_id']:r for r in read(optimization)['records']} if optimization and Path(optimization).exists() else {}
    rows=[]; matrix=[]
    for rec in a['records']:
        rid=rec['record_id']; lookup={m['model']:m for m in rec['results']}
        if set(lookup)!=set(MODELS):raise ValueError(f'{rid}: missing/extra model')
        if rid in old and not old[rid]['exact_chain_local']: raise ValueError(f'{rid}: not local in v0.23')
        for m in MODELS:
            x=lookup[m];p=int(m[-1]) if m!='uniform' else 0
            if x['shots']<1 or x['optimum_hits']>x['shots']:raise ValueError('Bad hit counts')
            if abs(x['optimum_hits']/x['shots']-x['optimum_probability'])>1e-10:raise ValueError('Probability/hits mismatch')
            if not math.isclose(sum(x['state_probabilities']),1,abs_tol=1e-8):raise ValueError('Distribution does not sum to one')
            v=old.get(rid,{}).get('circuits',{}).get(m,{})
            row={'record_id':rid,'stratum':rec.get('stratum',''),'model':m,'depth_p':p,
                 'shots':x['shots'],'hits':x['optimum_hits'],'n_optimal_states':rec['n_optimal_states'],
                 'uniform_ideal':rec['n_optimal_states']/256,
                 'hardware_optimum':x['optimum_probability'],'ideal_optimum':x['ideal_optimum_probability'],
                 'gap_pp':100*(x['optimum_probability']-x['ideal_optimum_probability']),
                 'retention_ratio':x['optimum_probability']/x['ideal_optimum_probability'] if x['ideal_optimum_probability']>0 else None,
                 'hardware_expected_energy':x['expected_energy'],'ideal_expected_energy':x['ideal_expected_energy'],
                 'energy_gap':x['expected_energy']-x['ideal_expected_energy'],
                 'cx_logical':v.get('cx'), 'depth_logical':v.get('depth'),
                 'feasible_probability':x.get('feasible_probability'),
                 'wilson_low':x['wilson_95'][0], 'wilson_high':x['wilson_95'][1]}
            rows.append(row)
        matrix.append({m:lookup[m]['optimum_probability'] for m in MODELS}|{'record_id':rid})
    n=len(matrix)
    agg={}
    for m in MODELS:
        group=[r for r in rows if r['model']==m]
        agg[m]={'hardware_mean':mean([r['hardware_optimum'] for r in group]),
                'ideal_mean':mean([r['ideal_optimum'] for r in group]),
                'mean_gap_pp':mean([r['gap_pp'] for r in group]),
                'mean_retention_ratio':mean([r['retention_ratio'] for r in group]),
                'ratio_of_means':sum(r['hardware_optimum'] for r in group)/sum(r['ideal_optimum'] for r in group),
                'energy_gap_mean':mean([r['energy_gap'] for r in group])}
    comparisons={}
    for hi,lo in [('p1','uniform'),('p2','p1'),('p3','p2'),('p3','p1'),('p3','uniform')]:
        dif=[z[hi]-z[lo] for z in matrix]
        comparisons[f'{hi}_minus_{lo}']={'mean_difference_pp':100*mean(dif),'positive':sum(d>1e-12 for d in dif),
           'negative':sum(d < -1e-12 for d in dif),'ties':sum(abs(d)<=1e-12 for d in dif),
           'exact_p_two_sided':paired_test(dif),'bootstrap_95_pp':[100*v for v in ci_bootstrap(dif)]}
    wins={m:0 for m in ('p1','p2','p3')};ties=0
    for r in matrix:
        top=max(r[m] for m in wins)
        best=[m for m in wins if abs(r[m]-top)<1e-12]
        if len(best)==1:wins[best[0]]+=1
        else:ties+=1
    corr={}
    for m in ('p1','p2','p3'):
        group=[r for r in rows if r['model']==m]
        for v in ('cx_logical','depth_logical'):
            filt=[r for r in group if r[v] is not None]
            corr[f'{m}_{v}_vs_gap_pp']=spearman([r[v] for r in filt],[r['gap_pp'] for r in filt]) if filt else None
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with (output/'per_record.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result={'version':'QHDE-v0.26','offline_only':True,'source_job':a['job_id'],'backend':a['backend'],
      'source_analysis_sha256':hashlib.sha256(Path(analysis).read_bytes()).hexdigest(),
      'n_records':n,'n_circuits':len(rows),'aggregates':agg,'paired_comparisons':comparisons,
      'winner_counts_no_ties':wins,'tied_winners':ties,'spearman_exploratory':corr,
      'methodological_notes':['Paired tests use songs/instances as units, not 1024 shots as independent songs.',
       'Music cases may share Hamiltonian landscapes; song-level confidence intervals may overstate independent information.',
       'Per-instance Wilson intervals capture shot uncertainty, not device drift or instance-sampling uncertainty.',
       'CX/depth here come from v0.23 logical circuits, not backend-transpiled v0.25 circuits.',
       'Correlation of noise gap with depth is confounded by QAOA layer count and instance-specific effects.',
       'Global optimum is defined by the modeled corrected-EMH score, not human preference.',
       'No quantum advantage is claimed; 256 states are trivially classically enumerable.']}
    (output/'audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines=['# QHDE v0.26: offline hardware–ideal gap audit','',f'Job `{a["job_id"]}`, backend `{a["backend"]}`, {n} instances, {len(rows)} circuits.','',
       '| Model | Hardware (%) | Ideal (%) | Gap (pp) | Ratio of means |','|---|---:|---:|---:|---:|']
    for m in MODELS:
        s=agg[m];lines.append(f'| {m} | {100*s["hardware_mean"]:.2f} | {100*s["ideal_mean"]:.2f} | {s["mean_gap_pp"]:+.2f} | {s["ratio_of_means"]:.3f} |')
    lines.extend(['','## Paired hardware comparisons','', '| Pair | Mean difference (pp) | Positive/negative/tied | Exact sign-flip p | 95% bootstrap CI (pp) |','|---|---:|---:|---:|---:|'])
    for k,s in comparisons.items():
        ci=s['bootstrap_95_pp'];lines.append(f'| {k} | {s["mean_difference_pp"]:+.2f} | {s["positive"]}/{s["negative"]}/{s["ties"]} | {s["exact_p_two_sided"]:.4f} | [{ci[0]:.2f}, {ci[1]:.2f}] |')
    lines.extend(['','## Caveats','']+['- '+x for x in result['methodological_notes']])
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'OK v0.26: {n} instances, {len(rows)} circuits; hardware winners={wins}, ties={ties}')
    for m in MODELS:print(m, f'{100*agg[m]["hardware_mean"]:.2f}% vs {100*agg[m]["ideal_mean"]:.2f}% ideal')
    print('SAVED',output/'REPORT.md',output/'audit.json',output/'per_record.csv')
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--analysis',default='QHDE/results/ibm_v25/analysis.json');ap.add_argument('--audit-v23',default='QHDE/results/structured_v23/audit.json');ap.add_argument('--optimization-v24',default='QHDE/results/optimize_v24/optimization.json');ap.add_argument('--out',default='QHDE/results/audit_v26');args=ap.parse_args()
    run(args.analysis,args.audit_v23,args.optimization_v24,args.out)
