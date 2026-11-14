"""QHDE v0.32: harmonic-dependency ablation + practical routing (offline)."""
import argparse,csv,hashlib,json,zipfile
from pathlib import Path
import numpy as np


def loads_source(path):
    z=zipfile.ZipFile(path) if str(path).endswith('.zip') else None
    def load(name):
        return json.loads(z.read(name)) if z else json.loads((Path(path)/name).read_text())
    m=load('manifest.json');return m,load

def calc_scores(unary,pairs):
    unary=np.asarray(unary,float);pairs=np.asarray(pairs,float)
    if unary.shape!=(4,4) or pairs.shape!=(3,4,4):raise ValueError('Expected four unary tables and three 4x4 transitions')
    states=np.stack(np.unravel_index(np.arange(256),(4,)*4),axis=1)
    return (sum(unary[i,states[:,i]] for i in range(4))+
            sum(pairs[i,states[:,i],states[:,i+1]] for i in range(3)))

def local_choice(unary):
    return tuple(int(x) for x in np.argmax(np.asarray(unary),axis=1))

def index_of(state):return int(state[0]*64+state[1]*16+state[2]*4+state[3])

def dp_chain(unary,pairs):
    u=np.asarray(unary,float);t=np.asarray(pairs,float)
    v=u[0].copy();paths=[(j,) for j in range(4)]
    for i in range(1,4):
        candidates=v[:,None]+t[i-1];winner=np.argmax(candidates,axis=0)
        v=u[i]+candidates[winner,np.arange(4)]
        paths=[paths[int(winner[j])]+(j,) for j in range(4)]
    j=int(np.argmax(v));return float(v[j]),index_of(paths[j])

def shuffle_pairs(pairs,seed):
    t=np.asarray(pairs,float).copy();rng=np.random.default_rng(seed)
    for i in range(3):
        # Permute cell associations independently per edge while preserving exactly the 16 values.
        t[i]=rng.permutation(t[i].ravel()).reshape(4,4)
    return t

def info_gain(regret,threshold):return float(regret>threshold)

def summarize(rows,threshold):
    if not rows:return {'n':0}
    r=np.asarray([x['regret_actual_normalized'] for x in rows]);g=np.asarray([x['gain_over_shuffled_mean_normalized'] for x in rows]);
    pred=r>threshold
    return {'n':len(rows),'mean_regret':float(np.mean(r)),'median_regret':float(np.median(r)),
            'fraction_need_joint':float(np.mean(pred)),'mean_actual_minus_shuffled':float(np.mean(g))}

def run(source,out,seed=42,shuffles=30,threshold=0.02,limit=0):
    m,load=loads_source(source)
    if m.get('version')!='QHDE-v0.29':raise ValueError('Expected v0.29 manifest')
    if shuffles<1:raise ValueError('shuffles must be >=1')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rows=[];bad=[];allrecords=m['records'][:limit] if limit else m['records']
    for j,r in enumerate(allrecords):
        d=load(r['file']);u=np.asarray(d['unary_scores'],float);t=np.asarray(d['transition_scores'],float)
        full=calc_scores(u,t)
        recorded=np.asarray([np.nan if x is None else x for x in d['scores_256']],float)
        feasible=np.isfinite(recorded)
        if feasible.sum()!=r['n_feasible']:raise ValueError('Mask mismatch '+r['record_id'])
        if not np.allclose(full[feasible],recorded[feasible],atol=1e-8):
            raise ValueError('EMH decomposition failed: '+r['record_id'])
        # For restricted tasks, original score table has non-factorizing feasibility constraints.
        # Keep same feasible mask for ALL ablations; use exact 256 enumeration for fair comparisons.
        original=full.copy(); original[~feasible]=-np.inf
        opt=float(np.max(original));arg=int(np.argmax(original)); span=float(np.ptp(original[feasible]));span=max(span,1e-12)
        naive=index_of(local_choice(u));naive_valid=bool(feasible[naive])
        naive_score=float(original[naive]) if naive_valid else None
        # Feasible independent ranking is defined by the unary-only optimum under SAME mask.
        unary=calc_scores(u,np.zeros_like(t)); unary[~feasible]=-np.inf
        unary_idx=int(np.argmax(unary));unary_in_actual=float(original[unary_idx]);
        regret=max(0.,(opt-unary_in_actual)/span)
        shuffled=[]
        for k in range(shuffles):
            tt=shuffle_pairs(t,seed+100003*j+7919*k)
            z=calc_scores(u,tt);z[~feasible]=-np.inf
            idx=int(np.argmax(z));shuffled.append(max(0.,(opt-original[idx])/span))
        s_mean=float(np.mean(shuffled))
        dpscore,dpidx=dp_chain(u,t)
        if feasible.all() and (abs(dpscore-opt)>1e-8 or abs(original[dpidx]-opt)>1e-8):
            raise ValueError('DP mismatch '+r['record_id'])
        rows.append({'record_id':r['record_id'],'landscape_hash':r['landscape_hash'],
            'partition':r['partition'],'clean_validation':int(bool(r.get('leakage_safe_validation',False)) and r['partition']=='internal_validation'),
            'stratum':r['stratum'],'n_feasible':int(feasible.sum()),'score_span':span,
            'full_optimum_score':opt,'unary_only_choice_index':unary_idx,'original_optimum_index':arg,
            'regret_actual_normalized':regret,'shuffled_decision_regret_mean_normalized':s_mean,
            'gain_over_shuffled_mean_normalized':s_mean-regret,
            'naive_argmax_feasible':int(naive_valid),'naive_argmax_score':naive_score,
            'dp_exact_applicable':int(bool(feasible.all())),
            'reference_entropy_bits':r.get('conditional_transition_entropy_bits'),
            'reference_repeated_bigram_rate':r.get('repeated_bigram_rate')})
    # Fit a fixed cutoff (provided before seeing data). Do not train on validation records.
    train=[r for r in rows if r['partition']=='internal_train' and r['n_feasible']==256]
    valid=[r for r in rows if r['clean_validation'] and r['n_feasible']==256]
    for subset in (train,valid):
        for r in subset:r['route_joint_if_regret_over_threshold']=int(r['regret_actual_normalized']>threshold)
    # Avoid leakage: exact regret requires already evaluating joint optimum. Router is an
    # ORACLE DIAGNOSTIC, not a deployable prediction. Practical DP is computationally cheap.
    report=['# QHDE v0.32 — harmonic-dependency ablation and practical routing audit','',
      f'- Instances: **{len(rows)}**; landscapes: **{len(set(r["landscape_hash"] for r in rows))}**.',
      '- Full score factorization numerically checked on feasible states for every instance.',
      '- All ablations retain exactly the same feasibility mask; restricted cases require exact enumeration.',
      '- Unary-only decision selects feasible maximizer of sum of unary scores; compare its TRUE original EMH score against joint optimum.',
      '- Shuffled-transition controls permute each 4x4 transition matrix (same multiset of 16 values), then optimize under the original feasibility mask and evaluate the resulting choice on ORIGINAL EMH.',
      '- Shuffling is a negative control, not a valid musical alternative or a matched Hamiltonian complexity control.',
      '- Full-feasible cases have an exact O(3*4^2) dynamic-programming solver; validated against exhaustive enumeration.',
      '- Routing by actual regret is an ORACLE analysis and cannot be deployed without computing the joint optimum; DP itself is the practical default.',
      '- NOT a QAOA run: existing v0.30 QAOA results remain a separate optimization study.',
      '', '| Subset | n | Mean loss unary vs joint (normalized) | Mean benefit correct over shuffled links (normalized) |',
      '|---|---:|---:|---:|']
    sets=[('all',rows),('fully feasible',[r for r in rows if r['n_feasible']==256]),('restricted',[r for r in rows if r['n_feasible']<256]),('training full feasible',train),('validation full feasible',valid)]
    for name,s in sets:
        if s: report.append(f'| {name} | {len(s)} | {np.mean([r["regret_actual_normalized"] for r in s]):.4f} | {np.mean([r["gain_over_shuffled_mean_normalized"] for r in s]):.4f} |')
    report+=['','## Practical decision','',
      f'- Diagnostic cutoff: {threshold:.3f} of original feasible score span, **fixed before analysis**.',
      '- The scientifically valid deployable baseline is dynamic programming for fully feasible four-chord chains, not QAOA.',
      '- For masked tasks the non-factorizing feasibility constraints invalidate simple DP; check mask structure before considering an efficient constrained solver.',
      '- Next test: fit a genuinely cheap router from unary-only statistics and compare validation cost/quality against always-DP and always-unary.',
      '- Distinct landscape hashes do not guarantee independent songs. HookTheory TRAIN-only validation is not external validation.',
      '- Do not interpret the shuffled-transition comparison as causal evidence of musical meaning without independent human evaluation.', '']
    with (out/'per_instance.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (out/'REPORT.md').write_text('\n'.join(report))
    (out/'audit.json').write_text(json.dumps({'version':'v0.32','n':len(rows),'n_unique':len(set(r['landscape_hash'] for r in rows)),
       'seed':seed,'shuffles':shuffles,'threshold':threshold,'summaries':{name:summarize(s,threshold) for name,s in sets},
       'no_qpu':True,'qaoa_not_rerun':True},indent=2)+'\n')
    print(f'OK v0.32: {len(rows)} records, {len(set(r["landscape_hash"] for r in rows))} unique. SAVED {out}/REPORT.md')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--source',default='QHDE/results/expanded_v29_full');a.add_argument('--out',default='QHDE/results/ablation_v32');a.add_argument('--seed',type=int,default=42);a.add_argument('--shuffles',type=int,default=30);a.add_argument('--threshold',type=float,default=.02);a.add_argument('--limit',type=int,default=0);x=a.parse_args();run(x.source,x.out,x.seed,x.shuffles,x.threshold,x.limit)
