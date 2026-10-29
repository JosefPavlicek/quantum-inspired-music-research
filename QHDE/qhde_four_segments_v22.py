"""QHDE v0.22: genuine four-segment, 8-qubit harmony instance construction.

Offline only. Reads HookTheory melody, uses HARMONIX corrected candidate vocabulary
and frozen EMH local/transition scoring. Human harmony is NOT read for scoring.
The objective is a chain of FOUR chord decisions, NOT independent pair scores.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'QHDE'))
FIXED = (0, 2, 4, 6)

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path, data):
    path=Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')

def four_scores(segments, key, scale, env, indices=FIXED, whole_song=False):
    """Score all 4^4 chains with EMH local terms and consecutive transitions.

    Each note segment is scored exactly once. Cadence final flag only if the
    fourth segment is actually the end of the song. Does not read ground truth.
    Basis index is c0*64+c1*16+c2*4+c3 (8-bit big-endian representation).
    """
    if len(segments)!=4: raise ValueError('Exactly four consecutive segments required')
    if len(indices)!=4 or len(set(indices))!=4: raise ValueError('Four distinct indices required')
    allc=[env['ChordCandidate'](c.symbol,c.roman,c.pitch_classes,c.function)
          for c in env['generate'](key.tonic,key.mode,'corrected')]
    if len(allc)!=10 or any(i<0 or i>=10 for i in indices): raise ValueError('Expected corrected 10 candidate vocabulary')
    cand=[allc[i] for i in indices]
    s=env['scoring']; conf=env['config']; w=(conf or {}).get('scoring',{}).get('weights')
    local=s['local_score']; melody=s['melody_compatibility']; transition=s['functional_transition']
    persist=s['persistence'];cadence=s['cadential_score']; sound=s['segment_has_sounding_notes']
    unary=np.empty((4,4),float);pair=np.empty((3,4,4),float)
    for t in range(4):
        for j,c in enumerate(cand):
            unary[t,j]=local(melody(segments[t],c,scale,conf),
                             transition(None,c,conf) if t==0 else 0.0,
                             persist(None,c,conf) if t==0 else 0.0,
                             cadence(None,c,bool(whole_song and t==3),conf), w)
            if not np.isfinite(unary[t,j]): raise ValueError('Nonfinite unary score')
    for t in range(1,4):
        for i,prev in enumerate(cand):
            for j,c in enumerate(cand):
                # Reproduce the published frozen scoring composition: difference
                # between transition-conditioned and reference-free local score.
                conditioned=local(melody(segments[t],c,scale,conf),
                    transition(prev,c,conf),persist(prev,c,conf),
                    cadence(None,c,bool(whole_song and t==3),conf),w)
                pair[t-1,i,j]=conditioned-unary[t,j]
    scores=[];invalid=[]
    for a in range(4):
      for b in range(4):
       for c in range(4):
        for d in range(4):
            seq=(a,b,c,d)
            possible=all(sound(segments[t]) or cand[seq[t-1]].roman==cand[seq[t]].roman
                         for t in range(1,4))
            index=a*64+b*16+c*4+d
            if not possible:
                invalid.append(index);scores.append(None);continue
            value=sum(unary[t,seq[t]] for t in range(4))
            value+=sum(pair[t-1,seq[t-1],seq[t]] for t in range(1,4))
            scores.append(float(value))
    return {'scores_256':scores,'invalid_indices':invalid,
        'candidate_indices':list(indices),
        'candidate_vocabulary':[{'index':indices[j], 'symbol':c.symbol,'roman':c.roman,'function':c.function}
            for j,c in enumerate(cand)],
        'n_feasible':256-len(invalid),'representation':'4 chord decisions x 2 qubits, 8 qubits total',
        'basis_order':'c0*64+c1*16+c2*4+c3',
        'unary_scores':unary.tolist(),'transition_scores':pair.tolist(),
        'is_final_segment_4':bool(whole_song)}

def normalized_energy(problem, invalid_penalty=2.0):
    scores=problem['scores_256']
    if len(scores)!=256:raise ValueError('Requires 256 basis states')
    a=np.array([np.nan if v is None else v for v in scores],float)
    good=np.isfinite(a)
    if not np.any(good):raise ValueError('No feasible harmonies')
    span=float(np.ptp(a[good]))
    if span<1e-12:raise ValueError('All feasible chains have identical scores')
    energy=np.full(256,float(invalid_penalty))
    energy[good]=-(a[good]-np.min(a[good]))/span
    best=float(np.max(a[good])); optimal=np.flatnonzero(good & np.isclose(a,best,rtol=0,atol=1e-10)).tolist()
    return energy,optimal

def build(selection, archive, out, limit=16):
    from qhde_hooktheory_export import build_env
    selected=json.loads(Path(selection).read_text(encoding='utf8'))
    if selected.get('split')!='TRAIN' or not selected.get('selection_only_reference_harmony'):
        raise ValueError('Requires v0.17 preselected TRAIN clips')
    if selected.get('archive_sha256') and selected['archive_sha256']!=sha(archive):
        raise ValueError('Corpus checksum mismatch')
    with gzip.open(archive,'rt',encoding='utf8') as f: corpus=json.load(f)
    env=build_env(); rows=[]; out=Path(out)
    for ix,item in enumerate(selected['selected'][:limit]):
        rid=item['record_id']; row={'record_id':rid,'stratum':item['stratum'],
              'music_features':{k:item.get(k) for k in ('n_chords','chord_entropy_bits','conditional_transition_entropy_bits','repeated_bigram_rate')}}
        try:
            rec=corpus[rid]
            melody=env['adapt'](env['melody_only'](rec))
            key=env['detect_key'](melody.notes)
            seg=env['segment_notes'](melody.notes,melody.time_signatures,env['config'])
            if len(seg)<4:raise ValueError(f'Only {len(seg)} melody segments')
            scale={p.pitchClass for p in env['Key'](key.tonic,key.mode).pitches}
            problem=four_scores(seg[:4],key,scale,env,whole_song=len(seg)==4)
            energy,optimal=normalized_energy(problem)
            problem['energies_256']=energy.tolist()
            problem['optimal_basis_indices']=optimal
            problem['uniform_optimum_probability']=len(optimal)/256
            problem['record_id']=rid;problem['total_song_segments']=len(seg)
            save(out/f'instance_{ix:03d}.json',problem)
            row.update(status='ok',file=f'instance_{ix:03d}.json',n_feasible=problem['n_feasible'],
                       n_optimal=len(optimal),total_song_segments=len(seg))
        except Exception as exc:
            row.update(status='failed',reason=f'{type(exc).__name__}: {exc}')
        print(f'{ix+1:02d}/{min(limit,len(selected["selected"]))} {rid}: {row["status"]}'+(' '+row.get('reason','') if row['status']=='failed' else ''))
        rows.append(row)
    manifest={'version':'QHDE-v0.22','offline_only':True,'split':'TRAIN',
        'source_selection_sha256':sha(selection),'source_archive_sha256':sha(archive),
        'scope':'first FOUR consecutive melody segments, corrected HARMONIX candidates, frozen EMH scores',
        'note':'Reference harmony used ONLY in frozen v0.17 selection; no original full-song entropy attribution to 4-segment circuit',
        'records':rows}
    save(out/'manifest.json',manifest)
    print(f'OK {sum(r["status"]=="ok" for r in rows)}/{len(rows)}; saved {out}/manifest.json; NO QPU JOB SUBMITTED')
    return manifest

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selection',default='QHDE/results/complexity_v17/selection.json')
    p.add_argument('--archive')
    p.add_argument('--out',default='QHDE/results/four_segments_v22')
    p.add_argument('--limit',type=int,default=16)
    a=p.parse_args()
    if a.limit<=0:p.error('--limit must be positive')
    if a.archive:archive=a.archive
    else:
        sys.path.insert(0,str(ROOT/'HARMONIX'))
        from harmonix.shared_data import require_hooktheory
        archive=require_hooktheory()
    build(a.selection,archive,a.out,a.limit)
if __name__=='__main__':main()
