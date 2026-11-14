"""QHDE v0.30: resumable offline batch QAOA using EXACT v0.24 optimize/simulate functions.

No QPU. Preserves corrected-EMH input scores and energies unchanged.
"""
import argparse, csv, hashlib, json, os, sys, time
from pathlib import Path
from collections import Counter
import numpy as np
from qhde_optimize_v24 import optimize, get_optimal, simulate

STAGES=(1,2,3)
def load_manifest(source):
    mpath=source/'manifest.json'; m=json.loads(mpath.read_text())
    if m.get('version')!='QHDE-v0.29' or m.get('n_valid')!=400: raise ValueError('Expected complete v0.29 source')
    rs=m['records']; assert len(rs)==400
    return m,hashlib.sha256(mpath.read_bytes()).hexdigest()

def assert_instance(r,d):
    e=np.asarray(d['energies_256'],float)
    f=np.array([x is not None for x in d['scores_256']],bool)
    if e.shape!=(256,) or not np.all(np.isfinite(e)):raise ValueError('Invalid energies')
    if len(d['scores_256'])!=256 or int(f.sum())!=r['n_feasible'] or int(f.sum())!=d['n_feasible']:raise ValueError('Bad feasible mask')
    if np.any(np.asarray(d['invalid_indices'],int)!=np.where(~f)[0]):raise ValueError('Invalid index list')
    if d['landscape_hash']!=r['landscape_hash'] or d['record_id']!=r['record_id']: raise ValueError('Instance vs manifest mismatch')
    true_opt=set(map(int,get_optimal(e,f))); declared=set(map(int,d['optimal_basis_indices']))
    if true_opt!=declared: raise ValueError('Reported optima differ from v0.24 exact optimum')
    return e,f

def record_run(source,r,starts,maxiter,seed):
    d=json.loads((source/r['file']).read_text());e,f=assert_instance(r,d)
    i=int(Path(r['file']).stem.split('_')[1]); models={};previous=None
    for p in STAGES:
        # Use the identical seeds as v0.24 for fixed instance order
        model=optimize(e,f,p,starts=starts,maxiter=maxiter,seed=seed+i*100+p,previous=previous)
        models['p'+str(p)]=model;previous=model['params']
    return {'record_id':r['record_id'],'instance_file':r['file'],'stratum':r['stratum'],
            'partition':r['partition'],'leakage_safe_validation':r.get('leakage_safe_validation',False),
            'n_feasible':int(f.sum()),'landscape_hash':r['landscape_hash'],
            'is_duplicate':bool(r.get('duplicate_of')),
            'baseline_uniform_optimum_probability':len(get_optimal(e,f))/256,
            'uniform_expected_energy':float(np.mean(e)),'models':models}

def make_reports(out,header,items):
    unique={}; rows=[]
    for x in items:
        unique.setdefault(x['landscape_hash'],x['record_id'])
        for p in STAGES:
            m=x['models']['p'+str(p)]
            rows.append({'record_id':x['record_id'],'partition':x['partition'],'stratum':x['stratum'],
              'n_feasible':x['n_feasible'],'landscape_hash':x['landscape_hash'],
              'validation_clean':int(x['partition']=='internal_validation' and x['leakage_safe_validation']),
              'depth':p,'expected_energy':m['expected_energy'],
              'ideal_optimum_probability':m['ideal_optimum_probability'],
              'ideal_feasible_probability':m['ideal_feasible_probability'],
              'uniform_optimum_probability':x['baseline_uniform_optimum_probability'],
              'optimizer_success':m['optimizer_success'],'best_nfev':m['optimizer_nfev_best_start']})
    if rows:
        with (out/'metrics.csv').open('w',newline='') as h:
            w=csv.DictWriter(h,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    counts=Counter(x['n_feasible'] for x in items)
    report=['# QHDE v0.30 — offline batch optimization (v0.24 optimizer)', '',
            f"- Source manifest SHA256: `{header['source_manifest_sha256']}`",
            f"- Completed instances: **{len(items)}**; distinct landscapes: **{len(unique)}**",
            f"- Feasibility counts: {dict(sorted(counts.items()))}",
            f"- Random starts per depth: **{header['starts']}**; maxiter: **{header['maxiter']}**; seed: **{header['seed']}**",
            '- No IBM QPU submitted; exact statevector QAOA, no hardware noise.',
            '- v0.24 objective: minimize expected energy INCLUDING infeasibility penalty; optimize p1/p2/p3 separately, warm-start p>1.',
            '- No classical speedup/quantum advantage claim. Feasible optima from exact enumeration of 256 states.',
            '- Source is HookTheory TRAIN only; internal clean validation is not an external holdout.',
            '- Validation leakage flag and landscape hashes retained; treat repeated musical-source clips as potentially dependent.', '',
            '| Subset | Records | Distinct landscapes |', '|---|---:|---:|']
    for label,subset in [('full (256 feasible)',[x for x in items if x['n_feasible']==256]),('restricted (<256 feasible)',[x for x in items if x['n_feasible']<256]),('internal train',[x for x in items if x['partition']=='internal_train']),('clean internal validation',[x for x in items if x['partition']=='internal_validation' and x['leakage_safe_validation']])]:
        report.append(f"| {label} | {len(subset)} | {len(set(x['landscape_hash'] for x in subset))} |")
    report+=['','## Mean ideal optimum probability (not hardware)', '', '| Depth | All | Full | Restricted |', '|---|---:|---:|---:|']
    for p in STAGES:
        vals=[]
        for subset in [items,[x for x in items if x['n_feasible']==256],[x for x in items if x['n_feasible']<256]]:
            vals.append(f"{100*np.mean([x['models']['p'+str(p)]['ideal_optimum_probability'] for x in subset]):.2f}%" if subset else 'n/a')
        report.append(f"| p={p} | {' | '.join(vals)} |")
    (out/'REPORT.md').write_text('\n'.join(report)+'\n')
    (out/'audit.json').write_text(json.dumps({**header,'n_completed':len(items),'n_unique':len(unique),'feasibility':dict(counts),
       'output_descriptions':{'metrics.csv':'all depth measurements','runs.jsonl':'resumable complete per-instance models'}},indent=2)+'\n')

def run(source,out,starts,maxiter,seed,limit,resume):
    source=Path(source);out=Path(out)
    manifest,sha=load_manifest(source)
    header={'version':'QHDE-v0.30','source_manifest_sha256':sha,'starts':starts,'maxiter':maxiter,'seed':seed,'optimizer':'qhde_optimize_v24.optimize','offline_only':True}
    if out.exists() and (out/'config.json').exists():
        old=json.loads((out/'config.json').read_text())
        if old!=header: raise ValueError('Existing output has incompatible configuration; use new --out')
        if not resume:raise FileExistsError('Existing run; pass --resume to continue')
    else:
        if out.exists() and any(out.iterdir()):raise FileExistsError('Existing nonempty output: choose new --out')
        out.mkdir(parents=True,exist_ok=True);(out/'config.json').write_text(json.dumps(header,indent=2)+'\n')
    ledger=out/'runs.jsonl';done={}
    if ledger.exists():
        for line in ledger.read_text().splitlines():
            if line.strip():
                x=json.loads(line);done[x['record_id']]=x
    selected=manifest['records'][:limit] if limit else manifest['records']
    for n,r in enumerate(selected,1):
        if r['record_id'] in done:continue
        start=time.monotonic(); x=record_run(source,r,starts,maxiter,seed)
        with ledger.open('a') as h:
            h.write(json.dumps(x,separators=(',',':'))+'\n');h.flush();os.fsync(h.fileno())
        done[x['record_id']]=x
        print(f"{n}/{len(selected)} {x['record_id']} feasible={x['n_feasible']} " + ' '.join(f"p{p}:{100*x['models']['p'+str(p)]['ideal_optimum_probability']:.2f}%" for p in STAGES) + f" {time.monotonic()-start:.1f}s",flush=True)
        if n%10==0:make_reports(out,header,list(done.values()))
    make_reports(out,header,list(done.values()))
    print('COMPLETE',len(done),'results in',out,'NO QPU',flush=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',default='QHDE/results/expanded_v29_full')
    ap.add_argument('--out',default='QHDE/results/optimize_v30')
    ap.add_argument('--starts',type=int,default=6)
    ap.add_argument('--maxiter',type=int,default=120)
    ap.add_argument('--seed',type=int,default=42)
    ap.add_argument('--limit',type=int,default=0,help='0=all 400')
    ap.add_argument('--resume',action='store_true')
    a=ap.parse_args()
    if a.starts<1 or a.maxiter<1 or a.limit<0:ap.error('Invalid limits')
    run(a.source,a.out,a.starts,a.maxiter,a.seed,a.limit,a.resume)
if __name__=='__main__':main()
