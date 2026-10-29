#!/usr/bin/env python3
"""Offline, reproducible audit of QHDE v0.18 vs v0.19. Stdlib only."""
import argparse, collections, csv, hashlib, itertools, json, math, random, statistics
from pathlib import Path

FIELDS=['record_id','stratum','n_chords','chord_entropy_bits','conditional_transition_entropy_bits','repeated_bigram_rate','n_optimal_states','full_optimum_represented','score_span','score_fingerprint','affine_fingerprint','uniform','p1','p2','p3','ideal_p1','ideal_p2','ideal_p3','delta_31','delta_32','ideal_delta_31','ideal_delta_32','noise_gap_p1','noise_gap_p2','noise_gap_p3','best_hardware_depth','best_ideal_depth','expected_score_p1','expected_score_p2','expected_score_p3']

def ranks(xs):
    order=sorted(range(len(xs)),key=lambda i:xs[i]); out=[0.]*len(xs); j=0
    while j<len(xs):
        k=j+1
        while k<len(xs) and xs[order[k]]==xs[order[j]]: k+=1
        for t in range(j,k):out[order[t]]=(j+1+k)/2
        j=k
    return out

def pearson(x,y):
    n=len(x); mx=sum(x)/n; my=sum(y)/n
    xx=sum((v-mx)**2 for v in x); yy=sum((v-my)**2 for v in y)
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/math.sqrt(xx*yy) if xx>1e-20 and yy>1e-20 else None

def spearman(x,y): return pearson(ranks(x),ranks(y))

def permutation_p(x,y,iterations=9999,seed=42):
    rho=spearman(x,y)
    if rho is None:return None
    rng=random.Random(seed); shuffled=list(y); exceed=0
    for _ in range(iterations):
        rng.shuffle(shuffled)
        r=spearman(x,shuffled)
        if r is not None and abs(r)>=abs(rho)-1e-12:exceed+=1
    return (exceed+1)/(iterations+1)

def fp(scores,affine=False):
    nums=[float(x) for x in scores]
    if affine:
        lo=min(nums); hi=max(nums)
        nums=[(v-lo)/(hi-lo) for v in nums] if hi-lo>1e-12 else [0.]*len(nums)
    else:
        # Global score offsets do not affect QAOA output probabilities.
        base=sum(nums)/len(nums);nums=[v-base for v in nums]
    return hashlib.sha256(json.dumps([round(v,8) for v in nums],separators=(',',':')).encode()).hexdigest()[:16]

def groups(rows,key):
    d=collections.defaultdict(list)
    for row in rows:d[row[key]].append(row['record_id'])
    return [sorted(ids) for ids in d.values() if len(ids)>1]

def run(instances,analysis,permutations=4999):
    a={r['record_id']:r for r in analysis['records']}; b={r['record_id']:r for r in instances['records']}
    if set(a)!=set(b):raise ValueError('Record ID mismatch: only in analysis '+str(set(a)-set(b))+'; only in instances '+str(set(b)-set(a)))
    rows=[]; warnings=[]
    for rid in sorted(b):
        x=b[rid]; y=a[rid]
        if x['status']!='ok':raise ValueError('Incomplete instance '+rid)
        if x['stratum']!=y['stratum']:raise ValueError('Stratum mismatch '+rid)
        scores=x['reduction']['scores_16']
        if len(scores)!=16:raise ValueError('Expected 16 scores for '+rid)
        outcomes={r['model']:r for r in y['results']}
        if set(outcomes)!={'uniform','p1','p2','p3'}:raise ValueError('Missing model '+rid)
        m=x['models']; feats=x['music_features']; row={'record_id':rid,'stratum':x['stratum']}
        for key in ('n_chords','chord_entropy_bits','conditional_transition_entropy_bits','repeated_bigram_rate'):row[key]=feats[key]
        row.update(n_optimal_states=len(x['reduction']['optimal_basis_indices']),full_optimum_represented=x['reduction']['full_optimum_represented'],score_span=x['reduction']['score_span'],score_fingerprint=fp(scores),affine_fingerprint=fp(scores,True))
        for depth in ('uniform','p1','p2','p3'):
            z=outcomes[depth]
            if z['shots']!=1024: warnings.append(f'{rid}/{depth}: shots={z["shots"]}')
            if sum(z['state_probabilities'])<.999 or sum(z['state_probabilities'])>1.001:raise ValueError('Non-normalized measurement '+rid)
            row[depth]=z['optimum_probability']
            if depth!='uniform':
                row['ideal_'+depth]=m[depth]['ideal_optimum_probability']
                if abs(z['ideal_optimum_probability']-row['ideal_'+depth])>1e-8:raise ValueError('Ideal probability mismatch '+rid)
                row['noise_gap_'+depth]=row[depth]-row['ideal_'+depth]
                row['expected_score_'+depth]=z['expected_harmonic_score']
        if row['n_optimal_states']!=y['n_optimal_states']:raise ValueError('Optimal state count mismatch '+rid)
        row['delta_31']=row['p3']-row['p1'];row['delta_32']=row['p3']-row['p2']
        row['ideal_delta_31']=row['ideal_p3']-row['ideal_p1'];row['ideal_delta_32']=row['ideal_p3']-row['ideal_p2']
        row['best_hardware_depth']=min(('p1','p2','p3'),key=lambda depth:(-row[depth],int(depth[1])))
        row['best_ideal_depth']=min(('p1','p2','p3'),key=lambda depth:(-row['ideal_'+depth],int(depth[1])))
        rows.append(row)
    duplicate_groups=groups(rows,'score_fingerprint');affine_groups=groups(rows,'affine_fingerprint')
    feature_keys=['chord_entropy_bits','conditional_transition_entropy_bits','repeated_bigram_rate','n_chords']
    targets=['delta_31','delta_32','noise_gap_p3']
    tests=[]
    for f,t in itertools.product(feature_keys,targets):
        tests.append(dict(feature=f,target=t,spearman_rho=spearman([r[f] for r in rows],[r[t] for r in rows]),permutation_p_two_sided=permutation_p([r[f] for r in rows],[r[t] for r in rows],permutations,seed=42)))
    by_stratum=[]
    for key in sorted({r['stratum'] for r in rows}):
        rr=[r for r in rows if r['stratum']==key]
        by_stratum.append(dict(stratum=key,n=len(rr),mean_probabilities={k:statistics.mean(r[k] for r in rr) for k in ('uniform','p1','p2','p3')},best_depth_counts=dict(collections.Counter(r['best_hardware_depth'] for r in rr))))
    # Descriptive pair-level analyses; no pseudo-replication correction by pooling shots.
    summary=dict(version='QHDE-v0.20',offline_only=True,job_id=analysis.get('job_id'),backend=analysis.get('backend'),n_records=len(rows),n_unique_centered_landscapes=len(rows)-sum(len(g)-1 for g in duplicate_groups),n_unique_affine_landscapes=len(rows)-sum(len(g)-1 for g in affine_groups),centered_score_duplicate_groups=duplicate_groups,affine_score_duplicate_groups=affine_groups,full_optimum_represented=sum(bool(r['full_optimum_represented']) for r in rows),best_hardware_depth_counts=dict(collections.Counter(r['best_hardware_depth'] for r in rows)),best_ideal_depth_counts=dict(collections.Counter(r['best_ideal_depth'] for r in rows)),mean_probabilities={k:statistics.mean(r[k] for r in rows) for k in ('uniform','p1','p2','p3')},mean_ideal_probabilities={k:statistics.mean(r['ideal_'+k] for r in rows) for k in ('p1','p2','p3')},mean_noise_gaps={k:statistics.mean(r['noise_gap_'+k] for r in rows) for k in ('p1','p2','p3')},by_stratum=by_stratum,correlation_tests=tests,permutations=permutations,warnings=warnings,limitations=['16 selected TRAIN clips, not independent held-out data','full-clip harmonic features versus only first-two-segment optimization','near-duplicate scoring landscapes may reduce effective sample size','QAOA classical parameters optimized per task and depth; optimizer budget not controlled here','one QPU job, no repeated randomized calibration-drift blocks','model-score optimum over 16 states; not human-perceived musical quality','multiple exploratory correlation tests; unadjusted permutation p-values; not confirmatory inference','exact classical enumeration of 16 states is trivial; no quantum advantage claim'])
    return rows,summary

def write(rows,summary,out):
    out.mkdir(parents=True,exist_ok=True)
    with (out/'audit.csv').open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    (out/'audit.json').write_text(json.dumps({'summary':summary,'rows':rows},indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    lines=['# QHDE v0.20 – Complexity–Depth Audit','',f"**Backend/job:** {summary['backend']} / `{summary['job_id']}`",f"**Cases:** {summary['n_records']}; distinct centered landscapes: **{summary['n_unique_centered_landscapes']}**; distinct affine-normalized landscapes: **{summary['n_unique_affine_landscapes']}**.",f"**Full 100-pair optimum present in reduced task:** {summary['full_optimum_represented']}/{summary['n_records']}",'','## Hardware optimum-hit probability (macro mean across clips)','', '| Model | Mean measured P(optimum) |','|---|---:|']
    lines.extend(f"| {k} | {100*v:.2f}% |" for k,v in summary['mean_probabilities'].items())
    lines+=['','## Best depth (highest measured optimum-hit probability)','',str(summary['best_hardware_depth_counts']),'','## Exact duplicate score landscapes (after subtracting mean)','',str(summary['centered_score_duplicate_groups']),'','## Affine-normalized identical landscapes (after min-max normalization)','',str(summary['affine_score_duplicate_groups']),'','These are grouping diagnostics, not proof that two songs are the same. Affine normalization is only a comparison heuristic; it does not preserve dynamics at fixed QAOA gamma.','','## Per-stratum averages','', '| Stratum | N | uniform | p1 | p2 | p3 |','|---|---:|---:|---:|---:|---:|']
    for s in summary['by_stratum']:
        p=s['mean_probabilities'];lines.append(f"| {s['stratum']} | {s['n']} | "+' | '.join(f'{p[k]*100:.2f}%' for k in ('uniform','p1','p2','p3'))+' |')
    lines+=['','## Exploratory correlations (Spearman; unadjusted two-sided permutation tests)','', '| Feature | Outcome | rho | p |','|---|---|---:|---:|']
    for t in summary['correlation_tests']:
        rho=t['spearman_rho']; p=t['permutation_p_two_sided'];lines.append(f"| {t['feature']} | {t['target']} | {rho:.3f} | {p:.4f} |" if rho is not None else f"| {t['feature']} | {t['target']} | n/a | n/a |")
    lines+=['','## Interpretation safeguards','']+['- '+s for s in summary['limitations']]+['','**This report is descriptive/exploratory, not evidence of musical complexity determining useful circuit depth.**','']
    (out/'REPORT.md').write_text('\n'.join(lines),encoding='utf8')

def main():
    p=argparse.ArgumentParser();p.add_argument('--instances',type=Path,default=Path('QHDE/results/construct_v18/instances.json'));p.add_argument('--analysis',type=Path,default=Path('QHDE/results/ibm_v19/analysis.json'));p.add_argument('--out',type=Path,default=Path('QHDE/results/audit_v20'));p.add_argument('--permutations',type=int,default=4999);a=p.parse_args()
    i=json.loads(a.instances.read_text(encoding='utf8'));j=json.loads(a.analysis.read_text(encoding='utf8'))
    rows,summary=run(i,j,a.permutations);write(rows,summary,a.out)
    print('QHDE v0.20 OFFLINE AUDIT; records:',len(rows));print('Unique centered score landscapes:',summary['n_unique_centered_landscapes']);print('Unique affine-normalized score landscapes:',summary['n_unique_affine_landscapes']);print('Hardware best depth:',summary['best_hardware_depth_counts']);print('Mean optimum probability:',{k:round(v,4) for k,v in summary['mean_probabilities'].items()});print('Saved:',a.out/'REPORT.md',a.out/'audit.csv',a.out/'audit.json');print('NO QPU JOBS SUBMITTED')
if __name__=='__main__':main()
