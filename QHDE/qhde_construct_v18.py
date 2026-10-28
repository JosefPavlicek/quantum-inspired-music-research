"""QHDE v0.18: frozen, score-blind 4x4 instances from v0.17 selected HookTheory TRAIN clips.

This constructs *two-segment* instances; longer musical-dependency tasks are future work.
No IBM access. Run from repository root.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'QHDE'))
# Pre-registered selection, independent of joint pair scores and reference harmony.
FIXED_CANDIDATES=[0,2,4,6]

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def matrix_from_score(record):
    if record.get('candidate_variant')!='corrected' or record.get('candidate_count')!=10:
        raise ValueError('Expected corrected EMH 10-candidate score table')
    scores=np.full((10,10),np.nan)
    for pair in record['pairs']:
        i,j=int(pair['a_index']),int(pair['b_index'])
        if not (0<=i<10 and 0<=j<10) or np.isfinite(scores[i,j]):
            raise ValueError('Invalid / duplicate pair score')
        scores[i,j]=float(pair['score'])
    if not np.isfinite(scores).all():raise ValueError('Incomplete score matrix; do not impute')
    return scores

def reduce_fixed(scores,indices=FIXED_CANDIDATES):
    if len(indices)!=4 or len(set(indices))!=4 or not all(0<=i<10 for i in indices):
        raise ValueError('Exactly 4 different valid candidate indices required')
    sub=np.asarray(scores)[np.ix_(indices,indices)]
    full=float(np.max(scores)); best=float(np.max(sub)); span=float(np.ptp(sub))
    optimal=np.flatnonzero(np.isclose(sub.reshape(-1),best,rtol=0,atol=1e-10)).tolist()
    return {'a_indices':list(indices),'b_indices':list(indices),'scores_16':sub.reshape(-1).tolist(),
            'full_optimum':full,'subset_optimum':best,'full_optimum_represented':bool(np.isclose(best,full,rtol=0,atol=1e-10)),
            'optimal_basis_indices':optimal,'uniform_optimum_probability':len(optimal)/16,
            'score_span':span, 'degenerate':span<1e-12}

def prepare(selection,archive,out,seed=42,starts=32,include_opt=True):
    from qhde_hooktheory_export import build_env,evaluate_two_prefix_segments
    from qhde_hardware_v10 import optimize,np_state
    selection=Path(selection);archive=Path(archive);out=Path(out)
    metadata=json.loads(selection.read_text(encoding='utf8'))
    if metadata.get('split')!='TRAIN' or not metadata.get('selection_only_reference_harmony'):
        raise ValueError('Invalid v0.17 TRAIN selection / missing selection provenance')
    selected=metadata.get('selected',[])
    if not selected or len({r['record_id'] for r in selected})!=len(selected):raise ValueError('Empty or duplicate selection')
    if metadata.get('archive_sha256') and metadata['archive_sha256']!=digest(archive):
        raise ValueError('HookTheory archive differs from frozen v0.17 selection')
    with gzip.open(archive,'rt',encoding='utf8') as f: corpus=json.load(f)
    env=build_env(); out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for ix,item in enumerate(selected):
        rid=item['record_id'];row={'record_id':rid,'stratum':item['stratum'],'music_features':{
            k:item.get(k) for k in ('n_chords','chord_entropy_bits','conditional_transition_entropy_bits','repeated_bigram_rate')}}
        try:
            if rid not in corpus:raise ValueError('Missing corpus record')
            score=evaluate_two_prefix_segments(corpus[rid],env)
            score['record_id']=rid;score['source_split']='TRAIN'
            # Ensure strict full 100 pair coverage, otherwise explicitly mark as unsupported.
            mat=matrix_from_score(score)
            p=reduce_fixed(mat)
            row.update({'status':'ok','task':score.get('task'),'reduction':p})
            if include_opt and not p['degenerate']:
                from qhde_hardware_v10 import objective
                energies=-(np.array(p['scores_16'])-min(p['scores_16']))/p['score_span']
                optimum_mask=np.zeros(16,dtype=bool);optimum_mask[p['optimal_basis_indices']]=True
                models={}
                for depth in (1,2,3):
                    params,val=optimize(energies,depth,seed+1000*ix+100*depth,starts)
                    probabilities=np.abs(np_state(energies,params))**2
                    models[f'p{depth}']={'params':params.tolist(),'ideal_optimum_probability':float(probabilities[optimum_mask].sum()),
                          'ideal_expected_score':float(np.dot(probabilities,p['scores_16'])),
                          'ideal_distribution':probabilities.tolist()}
                row['models']=models
            dump(out/f'scores_{ix:03d}.json',score)
        except Exception as exc:
            row['status']='failed';row['reason']=f'{type(exc).__name__}: {exc}'
        rows.append(row)
        print(f'{ix+1:02d}/{len(selected)} {rid} {row["status"]} represented={row.get("reduction",{}).get("full_optimum_represented","n/a")}')
    payload={'version':'QHDE-v0.18','offline_only':True,'split':'TRAIN','seed':seed,'starts':starts,
      'selected_sha256':digest(selection),'archive_sha256':digest(archive),
      'rule':'fixed candidate indices [0,2,4,6] at each position; independent of pair score and reference harmony',
      'scope':'first two melody segments only; reference harmony used exclusively for earlier selection/strata',
      'warning':'No longer-sequence optimization; no QPU submission; score-based oracle requires classical precomputation.',
      'records':rows}
    dump(out/'instances.json',payload)
    ok=sum(r['status']=='ok' for r in rows);represented=sum(r.get('reduction',{}).get('full_optimum_represented',False) for r in rows)
    print(f'Saved {out}/instances.json ; successful={ok}/{len(rows)}, full-optimum-in-fixed-subset={represented}/{ok}')
    print('OFFLINE ONLY — NO IBM QPU ACCESS')
    return payload

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selection',default='QHDE/results/complexity_v17/selection.json')
    p.add_argument('--archive',default=None)
    p.add_argument('--out',default='QHDE/results/construct_v18')
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--starts',type=int,default=32)
    p.add_argument('--no-optimization',action='store_true')
    a=p.parse_args()
    if a.starts<0:p.error('--starts must be nonnegative')
    if a.archive:archive=a.archive
    else:
        sys.path.insert(0,str(ROOT/'HARMONIX'))
        from harmonix.shared_data import require_hooktheory
        archive=require_hooktheory()
    prepare(a.selection,archive,a.out,a.seed,a.starts,not a.no_optimization)
if __name__=='__main__':main()
