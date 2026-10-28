"""QHDE v0.15: offline decision-landscape audit, not musical-complexity estimation.
Run at repository root: python QHDE/qhde_structure_v15.py
No IBM access, no submissions, no dependencies outside Python stdlib.
"""
import argparse, csv, json, math
from pathlib import Path
from statistics import mean

DEFAULT_AUDIT = Path('QHDE/results/audit_v14/audit.json')
DEFAULT_OUT = Path('QHDE/results/structure_v15')

def shannon(probs):
    return -sum(p * math.log2(p) for p in probs if p > 0)

def pearson(xs, ys):
    if len(xs) < 3 or len(xs) != len(ys): return None
    ax,ay=mean(xs),mean(ys)
    a=sum((x-ax)*(y-ay) for x,y in zip(xs,ys))
    b=sum((x-ax)**2 for x in xs)*sum((y-ay)**2 for y in ys)
    return a/math.sqrt(b) if b else None

def audit_record(record):
    scores=record['scores_16']
    if len(scores)!=16: raise ValueError('Expected exactly 16 scores')
    ranked=sorted(set(scores),reverse=True)
    best=ranked[0]
    # Tolerances intentionally avoid spurious ties due to float rounding.
    tied=sum(math.isclose(s,best,rel_tol=1e-10,abs_tol=1e-10) for s in scores)
    if tied != record['num_tied_optima']: raise ValueError('Tie count disagrees with audit')
    probs=[max(0.,s-min(scores)) for s in scores]
    z=sum(probs)
    entropy=shannon([v/z for v in probs]) if z else 4.0
    result={r['model']:r for r in record['results']}
    return {
        'record_id':record['record_id'],
        'optimum_count':tied,
        'distinct_scores':len({round(s,10) for s in scores}),
        'range_score':max(scores)-min(scores),
        'best_second_distinct_gap':(best-ranked[1]) if len(ranked)>1 else 0.,
        'score_sd':math.sqrt(mean([(s-mean(scores))**2 for s in scores])),
        'shifted_score_entropy_bits':entropy,
        'uniform_success':result['uniform']['optimal_probability'],
        'p1_success':result['p1']['optimal_probability'],
        'p2_success':result['p2']['optimal_probability'],
        'delta_p2_minus_p1_pp':record['p2_minus_p1']['delta_percentage_points'],
        'p1_mean_score':result['p1']['expected_harmonic_score'],
        'p2_mean_score':result['p2']['expected_harmonic_score'],
        'delta_mean_score':result['p2']['expected_harmonic_score']-result['p1']['expected_harmonic_score'],
        'ideal_p1_success':result['p1']['ideal_optimal_probability'],
        'ideal_p2_success':result['p2']['ideal_optimal_probability'],
        'ideal_depth_gain_pp':100*(result['p2']['ideal_optimal_probability']-result['p1']['ideal_optimal_probability']),
        'measured_depth_gain_pp':record['p2_minus_p1']['delta_percentage_points'],
        'delta_95_ci_pp':record['p2_minus_p1']['normal_95_percentage_points'],
    }

def run(audit_path=DEFAULT_AUDIT,out=DEFAULT_OUT):
    data=json.loads(Path(audit_path).read_text(encoding='utf8'))
    if data.get('version')!='QHDE-v0.14':raise ValueError('Expected QHDE-v0.14 audit')
    rows=[audit_record(r) for r in data['records']]
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with (out/'landscapes.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    factors=['optimum_count','distinct_scores','range_score','best_second_distinct_gap','score_sd','shifted_score_entropy_bits']
    correlations={k:pearson([r[k] for r in rows],[r['measured_depth_gain_pp'] for r in rows]) for k in factors}
    report={'version':'QHDE-v0.15','offline_only':True,'n_records':len(rows),'source_job':data['job_id'],
        'records':rows,'exploratory_correlations':correlations,
        'critical_limitations':['These are optimization-score landscape descriptors, NOT independently measured musical-complexity features.',
          'Five related TRAIN cases are insufficient for inferential correlations or predictive claims.',
          'Model-selected 4x4 subset; original 10x10 task not solved by QAOA.',
          'Ideal p1/p2 differ before hardware noise: depth effect is not attributable to noise alone.',
          'Complexity analysis of full-song human chord sequences requires original HookTheory records and reliable parsing.',
          'Bit-to-basis mapping must be independently audited before final publication.']}
    (out/'landscapes.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    md=['# QHDE v0.15 — Offline landscape exploration','',
        '**Not yet musical-complexity research.** These descriptors summarize 16 model-defined scores, and are deliberately separated from independently measured full-song harmonic properties.','',
        '| Record | Tied optima | Distinct scores | Score SD | p2–p1 (pp) | Ideal p2–p1 (pp) |','|---|---:|---:|---:|---:|---:|']
    for r in rows:
        md.append(f"| {r['record_id']} | {r['optimum_count']} | {r['distinct_scores']} | {r['score_sd']:.4f} | {r['measured_depth_gain_pp']:+.2f} | {r['ideal_depth_gain_pp']:+.2f} |")
    md += ['', '## Exploratory associations (n=5; not inferential)', '']
    for k,v in correlations.items():md.append(f'- {k}: r = {v:+.3f}' if v is not None else f'- {k}: undefined')
    md+=['','## Next scientific stage','',
         'Use full HookTheory songs with verified chord annotations to compute independent musical features (transition entropy, harmonic vocabulary, functional diversity, non-diatonic rate, repetition); compare with circuit-depth response while controlling for optimization-landscape complexity. Do not infer full-song complexity from this two-segment score export.','',
         '## Limitations','']
    md += ['- '+x for x in report['critical_limitations']]
    (out/'REPORT.md').write_text('\n'.join(md)+'\n',encoding='utf8')
    for r in rows:print(f"{r['record_id']} ties={r['optimum_count']} distinct={r['distinct_scores']} p2-p1={r['measured_depth_gain_pp']:+.2f} pp")
    print('Wrote',out/'REPORT.md')
    print('NO IBM ACCESS / NO QPU SPEND')
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--audit',type=Path,default=DEFAULT_AUDIT)
    ap.add_argument('--out',type=Path,default=DEFAULT_OUT)
    args=ap.parse_args();run(args.audit,args.out)
