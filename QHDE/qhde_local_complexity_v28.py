"""QHDE v0.28: prespecified local decision-complexity audit, offline only.

Reuses EXACTLY the four unary matrices and three transition matrices frozen in
v0.22; these are MODEL-derived local descriptors (not reference-chord entropy).
No IBM submission and no refitting of HARMONIX or the measured QAOA circuits.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

METRICS=('unary_ambiguity_bits','unary_margin_mean','coupling_rms','coupling_to_unary_ratio',
         'frustration_loss','unary_optimum_in_global','near_optimal_fraction')
OUTCOMES=('hardware_gain_p3_p2','ideal_gain_p3_p2','hardware_noise_gap_p3')

def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def softmax_entropy(row):
    v=np.asarray(row,float);v=v-v.max();p=np.exp(v)/np.exp(v).sum()
    return float(-sum(x*math.log2(x) for x in p if x>0))
def scores_from_factors(unary,pair):
    u=np.asarray(unary,float);t=np.asarray(pair,float)
    if u.shape!=(4,4) or t.shape!=(3,4,4) or not np.isfinite(u).all() or not np.isfinite(t).all():
        raise ValueError('Expected finite 4x4 unary and 3x4x4 transition scores')
    out=np.empty(256,float)
    for ix in range(256):
        c=((ix>>6)&3,(ix>>4)&3,(ix>>2)&3,ix&3)
        out[ix]=sum(u[j,c[j]] for j in range(4))+sum(t[j,c[j],c[j+1]] for j in range(3))
    return out

def local_features(instance):
    u=np.asarray(instance['unary_scores'],float);t=np.asarray(instance['transition_scores'],float)
    reconstructed=scores_from_factors(u,t)
    originals=instance['scores_256']
    if len(originals)!=256:raise ValueError('Wrong number of states')
    if any(x is None for x in originals) or instance['n_feasible']!=256:
        raise ValueError('Only fully feasible local-chain instances are supported')
    if not np.allclose(reconstructed,np.asarray(originals,float),atol=1e-8,rtol=0):
        raise ValueError('Factor scores do not reproduce frozen 256-state EMH scores')
    # Fixed normalization ensures inter-instance scale comparisons are meaningful.
    span=float(np.ptp(reconstructed))
    if span<=1e-12:raise ValueError('Degenerate landscape')
    un=u/span;tr=t/span
    # Remove arbitrary row/column main effects from each transition to isolate
    # true cross-position dependence (ANOVA double centering).
    coupled=tr-tr.mean(axis=1,keepdims=True)-tr.mean(axis=2,keepdims=True)+tr.mean(axis=(1,2),keepdims=True)
    coupling_rms=float(np.sqrt(np.mean(coupled**2)))
    unary_centered=un-un.mean(axis=1,keepdims=True)
    unary_rms=float(np.sqrt(np.mean(unary_centered**2)))
    independent=tuple(int(x) for x in np.argmax(u,axis=1))
    ind_ix=independent[0]*64+independent[1]*16+independent[2]*4+independent[3]
    optimum=float(reconstructed.max());best_ind=float(reconstructed[ind_ix])
    # near-optimal threshold fixed at 5% of total score span, not tuned to results.
    return {
      'unary_ambiguity_bits':float(np.mean([softmax_entropy(row) for row in un])),
      'unary_margin_mean':float(np.mean([np.sort(row)[-1]-np.sort(row)[-2] for row in un])),
      'coupling_rms':coupling_rms,
      'coupling_to_unary_ratio':float(coupling_rms/(unary_rms+1e-12)),
      'frustration_loss':float((optimum-best_ind)/span),
      'unary_optimum_in_global':float(abs(optimum-best_ind)<=1e-9),
      'near_optimal_fraction':float(np.mean(reconstructed>=optimum-0.05*span-1e-12)),
      'score_reconstruction_max_error':float(np.max(np.abs(reconstructed-np.asarray(originals,float)))),
    }

def rho(x,y):
    a=np.asarray(x,float);b=np.asarray(y,float)
    if a.size<4 or a.std()<1e-12 or b.std()<1e-12:return None
    r=float(spearmanr(a,b).statistic)
    return r if math.isfinite(r) else None

def perm_p(x,y,r,reps,seed):
    rng=np.random.default_rng(seed);k=0
    for _ in range(reps):
        v=rho(x,rng.permutation(y))
        if v is not None and abs(v)>=abs(r)-1e-12:k+=1
    return (k+1)/(reps+1)

def bh(ps):
    n=len(ps);ordered=sorted(range(n),key=lambda i:ps[i]);result=[0]*n;last=1.
    for j in range(n-1,-1,-1):
        ix=ordered[j];last=min(last,ps[ix]*n/(j+1));result[ix]=last
    return result

def loo_mae(rows,cols,target,ridge=1.):
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    x=np.array([[r[c] for c in cols] for r in rows],float)
    y=np.array([r[target] for r in rows],float)
    prediction=[];baseline=[]
    for i in range(len(y)):
        other=np.arange(len(y))!=i
        model=make_pipeline(StandardScaler(),Ridge(alpha=ridge))
        model.fit(x[other],y[other]);prediction.append(float(model.predict(x[i:i+1])[0]))
        baseline.append(float(y[other].mean()))
    return {'mae_pp':float(np.mean(np.abs(y-prediction))*100),
            'baseline_mae_pp':float(np.mean(np.abs(y-baseline))*100)}

def run(instances,hardware,out,permutations=5000):
    instances=Path(instances);hardware=Path(hardware);out=Path(out)
    man=load(instances/'manifest.json');hw=load(hardware)
    if man.get('version')!='QHDE-v0.22' or hw.get('version')!='QHDE-v0.25':raise ValueError('Unexpected source version')
    manifest={r['record_id']:r for r in man['records'] if r['status']=='ok'}
    rows=[]
    for h in hw['records']:
        rid=h['record_id'];item=manifest[rid];src=instances/item['file'];ins=load(src)
        if ins['record_id']!=rid:raise ValueError(f'Instance ID mismatch: {rid}')
        f=local_features(ins)
        m={r['model']:r for r in h['results']}
        rows.append({'record_id':rid,'stratum':h.get('stratum'),
            'hardware_gain_p3_p2':m['p3']['optimum_probability']-m['p2']['optimum_probability'],
            'ideal_gain_p3_p2':m['p3']['ideal_optimum_probability']-m['p2']['ideal_optimum_probability'],
            'hardware_noise_gap_p3':m['p3']['ideal_optimum_probability']-m['p3']['optimum_probability'],
            **f})
    if len(rows)!=12 or len({r['record_id'] for r in rows})!=12:raise ValueError('Expected exactly 12 unique hardware cases')
    tests=[]
    for j,c in enumerate(METRICS):
      for k,target in enumerate(OUTCOMES):
        x=[r[c] for r in rows];y=[r[target] for r in rows];r=rho(x,y)
        tests.append({'predictor':c,'outcome':target,'rho':r,
          'permutation_p':perm_p(x,y,r,permutations,2800+j*31+k) if r is not None else None})
    valid=[a for a in tests if a['permutation_p'] is not None]
    for a,q in zip(valid,bh([x['permutation_p'] for x in valid])):a['fdr_q']=q
    predictors=[('local_margins',('unary_ambiguity_bits','unary_margin_mean')),
        ('interaction',('coupling_rms','frustration_loss')),
        ('combined',('unary_ambiguity_bits','coupling_rms','frustration_loss'))]
    predictions={name:loo_mae(rows,cols,'hardware_gain_p3_p2') for name,cols in predictors}
    out.mkdir(parents=True,exist_ok=True)
    with (out/'per_instance.csv').open('w',newline='',encoding='utf8') as fd:
      w=csv.DictWriter(fd,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (out/'correlations.csv').open('w',newline='',encoding='utf8') as fd:
      w=csv.DictWriter(fd,fieldnames=['predictor','outcome','rho','permutation_p','fdr_q']);w.writeheader();w.writerows(tests)
    audit={'version':'QHDE-v0.28','offline_only':True,'source_job':hw['job_id'],
      'scope':'four encoded melody segments / frozen corrected-EMH decision factors',
      'warning':'These are model-derived local decision descriptors, NOT HookTheory reference-harmony entropy.',
      'inputs_sha256':{'manifest':digest(instances/'manifest.json'),'hardware':digest(hardware)},
      'n_instances':len(rows),'tests':tests,'predictions':predictions}
    (out/'audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    report=['# QHDE v0.28: Local harmonic decision complexity','',
      f'- Hardware job: `{hw["job_id"]}`; **{len(rows)}** unique instances; no QPU use.',
      '- Descriptors reconstructed from the exact four unary and three transition score tables in v0.22.',
      '- **Not reference-harmony entropy**: no verified HookTheory alignment to the four segments has been performed.',
      '- Pair coupling removes unary effects by double centering; all scores normalized by 256-state score span.',
      '- Confirmed numerical equality of factorized and full 256-state scores for every instance.',
      '','## Correlations (exploratory; FDR over all nonconstant tests)','',
      '| Feature | Outcome | Spearman rho | permutation p | FDR q |','|---|---|---:|---:|---:|']
    for a in sorted(tests,key=lambda r:abs(r['rho'] or 0),reverse=True):
        fmt=lambda v:'NA' if v is None else f'{v:.3f}'
        report.append(f'| {a["predictor"]} | {a["outcome"]} | {fmt(a["rho"])} | {fmt(a["permutation_p"])} | {fmt(a.get("fdr_q"))} |')
    report+=['','## Leave-one-instance-out: hardware gain p3 minus p2','',
      '| Model | MAE (percentage points) | Mean-only baseline (pp) |','|---|---:|---:|']
    for name,p in predictions.items():report.append(f'| {name} | {p["mae_pp"]:.3f} | {p["baseline_mae_pp"]:.3f} |')
    report+=['','## Interpretation and limitations','',
      '- n=12; stratum-based nonrandom selection; correlations are descriptive, not causal.',
      '- 1024 shots per circuit and a single eight-qubit hardware run: winner labels are noisy.',
      '- All descriptors arise from the same EMH objective that defines the optimum: potential mathematical coupling, not independent human-validated music complexity.',
      '- We do not claim quantum advantage; 256 states can be enumerated classically.',
      '- Future genuinely musical local descriptors require independently verified annotation-to-segment temporal alignment.','']
    (out/'REPORT.md').write_text('\n'.join(report),encoding='utf8')
    print(f'QHDE v0.28: {len(rows)} local four-segment instances; {len(valid)} tests; no QPU submission')
    print('LOO:',predictions)
    print('SAVED',out/'REPORT.md',out/'audit.json',out/'per_instance.csv',out/'correlations.csv')
    return audit

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--instances',default='QHDE/results/four_segments_v22')
    p.add_argument('--hardware',default='QHDE/results/ibm_v25/analysis.json')
    p.add_argument('--out',default='QHDE/results/local_complexity_v28')
    p.add_argument('--permutations',type=int,default=5000)
    a=p.parse_args()
    if a.permutations<100:p.error('Use at least 100 permutations')
    run(a.instances,a.hardware,a.out,a.permutations)
if __name__=='__main__':main()
