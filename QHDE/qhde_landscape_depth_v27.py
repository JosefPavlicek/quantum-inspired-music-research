"""QHDE v0.27: offline landscape uniqueness and depth-prediction pilot.

No Qiskit, IBM authentication, or QPU submission. Requires frozen v0.22
instance files, v0.23 audit, v0.25 analysis. Full-song features are PROXIES,
not local four-segment music features. All inferences exploratory.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from pathlib import Path
import numpy as np

FEATURES=('chord_entropy_bits','conditional_transition_entropy_bits','repeated_bigram_rate',
          'landscape_std','landscape_gap','pair_variance_share','z_terms','cx_p3')
MUSIC=FEATURES[:3]

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rho(x,y):
    # scipy provided in HARMONIX venv; avoids misleading coefficient on constant arrays
    from scipy.stats import spearmanr
    x=np.asarray(x,float);y=np.asarray(y,float)
    if len(x)<4 or np.std(x)<1e-12 or np.std(y)<1e-12:return None
    v=float(spearmanr(x,y).statistic)
    return v if math.isfinite(v) else None

def permutation_p(x,y,observed,reps=20000,seed=27):
    rng=np.random.default_rng(seed);count=0
    for _ in range(reps):
        r=rho(x,rng.permutation(y));count+=r is not None and abs(r)>=abs(observed)-1e-12
    return (count+1)/(reps+1)

def bh(pvals):
    n=len(pvals);s=sorted(range(n),key=lambda i:pvals[i]);out=[None]*n;best=1.
    for rankidx in range(n-1,-1,-1):
        i=s[rankidx];best=min(best,pvals[i]*n/(rankidx+1));out[i]=best
    return out

def walsh(v):
    a=np.asarray(v,float).copy();h=1
    while h<len(a):
        for i in range(0,len(a),2*h):
            x=a[i:i+h].copy();y=a[i+h:i+2*h].copy()
            a[i:i+h]=x+y;a[i+h:i+2*h]=x-y
        h*=2
    return a/len(v)

def landscape_metrics(energy):
    e=np.asarray(energy,float)
    if e.shape!=(256,) or not np.all(np.isfinite(e)):
        raise ValueError('Expected 256 finite energies')
    v=np.sort(np.unique(np.round(e,10)))
    gap=float(v[1]-v[0]) if len(v)>1 else 0.
    c=walsh(e);tot=sum(float(z*z) for z in c[1:]);pair=0.;nonlocal_terms=0
    for mask,z in enumerate(c[1:],1):
        if abs(z)<1e-10:continue
        blocks={b//2 for b in range(8) if mask&(1<<b)}
        if len(blocks)>1 and max(blocks)-min(blocks)>1 or len(blocks)>2: nonlocal_terms+=1
        if len(blocks)==2 and max(blocks)-min(blocks)==1:pair+=float(z*z)
    return {'landscape_std':float(e.std()),'landscape_gap':gap,
            'pair_variance_share':pair/tot if tot>0 else 0.,'nonlocal_terms_recomputed':nonlocal_terms}

def grouping(rows,tol=1e-9):
    """Full energy vector: unique objective up to shift and positive scale.
    Distinguish exact scale-preserving and affine-equivalent landscapes.
    """
    groups=[]
    for r in rows:
        e=np.asarray(r['_energies'],float)
        centered=e-e.mean();span=float(np.ptp(centered))
        normal=centered/span if span>1e-12 else centered
        hit=None
        for gi,gr in enumerate(groups):
            if np.max(np.abs(normal-gr['norm']))<=tol:hit=gi;break
        if hit is None:
            groups.append({'norm':normal,'members':[r['record_id']]});hit=len(groups)-1
        else:groups[hit]['members'].append(r['record_id'])
        r['landscape_group']=hit+1
    return [g['members'] for g in groups]

def loo_ridge(rows,keys,target,alpha=1.0):
    # Standardization *inside* each train fold; ridge without feature leakage.
    X=np.array([[r[k] for k in keys] for r in rows],float);y=np.array([r[target] for r in rows],float)
    if not np.isfinite(X).all() or len(rows)<5:return None
    pred=[]
    for i in range(len(rows)):
        tr=np.arange(len(rows))!=i;mu=X[tr].mean(0);sd=X[tr].std(0);sd[sd<1e-12]=1.
        Z=(X[tr]-mu)/sd;target_train=y[tr];ym=target_train.mean()
        beta=np.linalg.solve(Z.T@Z+alpha*np.eye(len(keys)), Z.T@(target_train-ym))
        pred.append(float(ym+((X[i]-mu)/sd)@beta))
    baseline=np.array([np.mean(np.delete(y,i)) for i in range(len(y))]);pred=np.array(pred)
    return {'features':list(keys),'loo_mae_pp':float(np.mean(np.abs(pred-y))*100),
            'baseline_loo_mae_pp':float(np.mean(np.abs(baseline-y))*100),
            'loo_predictive_r2':float(1-np.sum((pred-y)**2)/np.sum((baseline-y)**2))
            if np.sum((baseline-y)**2)>0 else None}

def run(instances,audit,hardware,out):
    instances=Path(instances);audit=Path(audit);hardware=Path(hardware);out=Path(out)
    man=load(instances/'manifest.json');aud=load(audit);hw=load(hardware)
    if man.get('version')!='QHDE-v0.22' or aud.get('version')!='QHDE-v0.23' or hw.get('version')!='QHDE-v0.25':
        raise ValueError('Requires v0.22 manifest, v0.23 audit, v0.25 hardware data')
    by_manifest={r['record_id']:r for r in man['records'] if r['status']=='ok'}
    by_audit={r['record_id']:r for r in aud['records']}
    rows=[]
    for rec in hw['records']:
        rid=rec['record_id']
        if rid not in by_manifest or rid not in by_audit:
            raise ValueError(f'Missing source instance for {rid}')
        mr=by_manifest[rid];ar=by_audit[rid]
        if not ar['exact_chain_local']: raise ValueError(f'{rid} is not local, unexpected hardware entry')
        problem=load(instances/mr['file']);energies=problem['energies_256']
        if int(problem['n_feasible'])!=256: raise ValueError(f'{rid} infeasible states in local-only experiment')
        if int(rec['n_optimal_states'])!=len(problem['optimal_basis_indices']):raise ValueError(f'{rid} optimum multiplicity mismatch')
        probs={r['model']:r for r in rec['results']}
        if set(probs)!={'uniform','p1','p2','p3'}:raise ValueError(f'{rid} unexpected models')
        for mod,entry in probs.items():
            if abs(entry['optimum_hits']/entry['shots']-entry['optimum_probability'])>1e-10:
                raise ValueError(f'{rid}/{mod}: inconsistent hit count')
        f=mr.get('music_features',{})
        row={'record_id':rid,'stratum':rec.get('stratum'),
             'n_song_chords':f.get('n_chords'), 'n_song_segments':problem.get('total_song_segments'),
             'n_optimal_states':rec['n_optimal_states'],
             'z_terms':ar['n_nonzero_z_terms'],'cx_p3':ar['circuits']['p3']['cx'],
             'ideal_p3':probs['p3']['ideal_optimum_probability'],
             'hardware_p3':probs['p3']['optimum_probability'],
             'benefit_p3_vs_p2':probs['p3']['optimum_probability']-probs['p2']['optimum_probability'],
             'benefit_p2_vs_p1':probs['p2']['optimum_probability']-probs['p1']['optimum_probability'],
             'noise_gap_p3':probs['p3']['ideal_optimum_probability']-probs['p3']['optimum_probability'],
             'hardware_best':max(('p1','p2','p3'),key=lambda m:probs[m]['optimum_probability']),
             **landscape_metrics(energies), '_energies':energies}
        for k in MUSIC:row[k]=f.get(k)
        rows.append(row)
    if len(rows)!=12:raise ValueError(f'Expected 12 local IBM cases, found {len(rows)}')
    groups=grouping(rows)
    unique=[]
    for g in groups:unique.append(next(r for r in rows if r['record_id']==g[0]))
    targets=('benefit_p3_vs_p2','noise_gap_p3')
    corrs=[]
    for feature in FEATURES:
        for target in targets:
            for label,sample in [('all_songs',rows),('unique_landscapes',unique)]:
                v=[r for r in sample if r.get(feature) is not None]
                x=[r[feature] for r in v];y=[r[target] for r in v]
                r=rho(x,y);p=permutation_p(x,y,r) if r is not None else None
                corrs.append({'feature':feature,'target':target,'dataset':label,'n':len(v),
                              'spearman_rho':r,'permutation_p':p})
    for label in ('all_songs','unique_landscapes'):
        valid=[r for r in corrs if r['dataset']==label and r['permutation_p'] is not None]
        q=bh([r['permutation_p'] for r in valid])
        for r,val in zip(valid,q):r['fdr_bh_q']=val
    predictors=[]
    for label,sample in [('all_songs',rows),('unique_landscapes',unique)]:
        for keys in [MUSIC,('landscape_std','landscape_gap','pair_variance_share')]:
            if all(all(r.get(k) is not None for k in keys) for r in sample):
                val=loo_ridge(sample,keys,'benefit_p3_vs_p2')
                if val:predictors.append({'dataset':label,**val})
    out.mkdir(parents=True,exist_ok=True)
    csvrows=[{k:v for k,v in r.items() if k!='_energies'} for r in rows]
    with (out/'per_instance.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(csvrows[0]));w.writeheader();w.writerows(csvrows)
    with (out/'correlations.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['feature','target','dataset','n','spearman_rho','permutation_p','fdr_bh_q'],extrasaction='ignore')
        w.writeheader();w.writerows(corrs)
    summary={'version':'QHDE-v0.27','offline_only':True,'job_id':hw['job_id'],
             'inputs_sha256':{str(p):digest(p) for p in (instances/'manifest.json',audit,hardware)},
             'n_instances':len(rows),'n_unique_affine_normalized_landscapes':len(groups),
             'affine_landscape_groups':groups,'correlations':corrs,'loo_predictors':predictors,
             'exploratory_warning':('Music features are FULL-SONG HookTheory features, not four-segment-local metrics; '
                 'selection is stratified on these features; duplicate landscapes may be dependent; '
                 'multiple testing and small n make inference exploratory; '
                 'postselected best depth is noisy with 1024 shots; no quantum advantage.')}
    (out/'audit.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines=['# QHDE v0.27 — music, interaction structure, QAOA depth', '',
           f'- IBM job: `{hw["job_id"]}`; local 8-qubit instances: **{len(rows)}**',
           f'- Independent affine-normalized energy landscapes: **{len(groups)}**',
           '- Full-song harmonic entropy is a **proxy**, NOT a local four-segment measurement.',
           '- No new QPU time used.','', '## Repeated landscapes', '']
    for g in groups:
        if len(g)>1:lines.append('- Shared: '+', '.join(g))
    lines+=['','## Exploratory rank correlations (sorted by absolute rho)','',
            '| Predictor | Outcome | Dataset | n | Spearman rho | permutation p | FDR q |',
            '|---|---|---|---:|---:|---:|---:|']
    for c in sorted(corrs,key=lambda d:abs(d['spearman_rho'] or 0),reverse=True):
        fmt=lambda z: 'NA' if z is None else f'{z:.3f}'
        lines.append(f'| {c["feature"]} | {c["target"]} | {c["dataset"]} | {c["n"]} | {fmt(c["spearman_rho"])} | {fmt(c["permutation_p"])} | {fmt(c.get("fdr_bh_q"))} |')
    lines+=['','## Leave-one-out prediction vs mean-only baseline','',
            '| Dataset | Predictors | MAE (pp) | Baseline MAE (pp) | Predictive R² |',
            '|---|---|---:|---:|---:|']
    for x in predictors:
        lines.append(f'| {x["dataset"]} | {", ".join(x["features"])} | {x["loo_mae_pp"]:.3f} | {x["baseline_loo_mae_pp"]:.3f} | {x["loo_predictive_r2"]:.3f} |')
    lines+=['','## Limitations', '', '- '+summary['exploratory_warning'],
            '- Duplicate groups are exact only up to the declared 1e-9 tolerance on normalized 256-state energies.',
            '- This assesses predictive association, NOT causality or a validated depth recommendation.',
            '- The 4-segment-local music descriptors require a separate, prespecified extraction protocol.', '']
    (out/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f'QHDE v0.27: {len(rows)} local instances; {len(groups)} unique affine-normalized landscapes')
    print('Duplicate groups:',[g for g in groups if len(g)>1])
    print('SAVED',out/'REPORT.md',out/'audit.json',out/'per_instance.csv',out/'correlations.csv')
    print('NO QPU JOB SUBMITTED')
    return summary

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--instances',default='QHDE/results/four_segments_v22')
    ap.add_argument('--audit-v23',default='QHDE/results/structured_v23/audit.json')
    ap.add_argument('--analysis-v25',default='QHDE/results/ibm_v25/analysis.json')
    ap.add_argument('--out',default='QHDE/results/landscape_depth_v27')
    a=ap.parse_args();run(a.instances,a.audit_v23,a.analysis_v25,a.out)
if __name__=='__main__':main()
