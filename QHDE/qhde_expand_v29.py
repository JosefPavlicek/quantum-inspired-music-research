"""QHDE v0.29: expand reference-blind 4-chord tasks from audited HookTheory TRAIN.

Offline only. Selection from reference harmony precedes all EMH scoring.
Internal train/validation partitions are NOT independent HookTheory TEST data.
"""
from __future__ import annotations
import argparse, csv, gzip, hashlib, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'QHDE'))
from qhde_music_complexity_v16 import DEFAULT_MANIFEST,select_train,stable_digest
from qhde_complexity_selection_v17 import analyze,select,PILOT_IDS
from qhde_four_segments_v22 import four_scores,normalized_energy,save

def canonical_landscape(energies, tol=1e-9):
    e=np.asarray(energies,float)
    if e.shape!=(256,) or not np.isfinite(e).all(): raise ValueError('256 finite energies needed')
    # Normalize by range of *feasible* energies separately; penalized states retained
    mn=float(e.min());span=float(np.ptp(e))
    if span<1e-12: raise ValueError('constant landscape')
    return tuple(np.rint((e-mn)/span/tol).astype(np.int64).tolist())

def split_for_id(record_id, seed='QHDE-v29-locked-split', train_fraction=.8):
    h=hashlib.sha256((seed+'|'+record_id).encode()).digest()
    return 'internal_train' if int.from_bytes(h[:8],'big')/2**64 < train_fraction else 'internal_validation'

def generate(archive, manifest, output, per_stratum=100, min_chords=8, max_records=0, seed='QHDE-v29-locked-split'):
    from qhde_hooktheory_export import build_env
    out=Path(output)
    if out.exists() and (out/'manifest.json').exists():
        raise FileExistsError(f'{out}/manifest.json exists: use a NEW output directory to avoid contamination')
    obj=json.loads(Path(manifest).read_text(encoding='utf8'))
    ids=select_train(obj,0)
    with gzip.open(archive,'rt',encoding='utf8') as f: corpus=json.load(f)
    summary=[analyze(corpus[rid],rid) if rid in corpus else {'record_id':rid,'status':'missing'} for rid in ids]
    selected,meta=select(summary,per_stratum,min_chords,PILOT_IDS)
    # Freeze selection order with deterministic original rule; optional maximum is a pilot only.
    if max_records: selected=selected[:max_records]
    env=build_env();rows=[];seen={}
    for i,item in enumerate(selected):
        rid=item['record_id'];row={'record_id':rid,'stratum':item['stratum'],
            'partition':split_for_id(rid,seed), 'status':'failed',
            'chord_entropy_bits':item['chord_entropy_bits'],
            'conditional_transition_entropy_bits':item['conditional_transition_entropy_bits'],
            'repeated_bigram_rate':item['repeated_bigram_rate']}
        try:
            rec=corpus[rid]
            melody=env['adapt'](env['melody_only'](rec))
            key=env['detect_key'](melody.notes)
            segments=env['segment_notes'](melody.notes,melody.time_signatures,env['config'])
            if len(segments)<4:raise ValueError('fewer than 4 melody segments')
            scale={p.pitchClass for p in env['Key'](key.tonic,key.mode).pitches}
            task=four_scores(segments[:4],key,scale,env,whole_song=(len(segments)==4))
            energies,optima=normalized_energy(task)
            # Distinct affine normalized score landscapes, with feasibility mask included.
            # Energy penalty not part of score normalization for fingerprinting.
            scores=np.array([float(x) if x is not None else np.nan for x in task['scores_256']])
            feasible=np.isfinite(scores)
            if not feasible.any():raise ValueError('no feasible solutions')
            good=scores[feasible]; span=float(np.ptp(good))
            if span<=1e-12:raise ValueError('constant feasible scores')
            scaled=np.rint(((good-good.min())/span)*1e9).astype(np.int64)
            digest=hashlib.sha256(feasible.astype(np.uint8).tobytes()+scaled.tobytes()).hexdigest()
            row.update(status='ok',n_feasible=int(feasible.sum()),n_optimal=len(optima),
                n_segments=len(segments),landscape_hash=digest,duplicate_of=seen.get(digest,''))
            if digest not in seen:seen[digest]=rid
            task.update(record_id=rid,energies_256=energies.tolist(),optimal_basis_indices=optima,
                total_song_segments=len(segments),landscape_hash=digest)
            filename=f'instance_{i:04d}.json';save(out/filename,task);row['file']=filename
        except Exception as exc:row['reason']=f'{type(exc).__name__}: {exc}'
        rows.append(row)
        if (i+1)%25==0 or i+1==len(selected):
            print(f'{i+1}/{len(selected)} processed; valid={sum(r["status"]=="ok" for r in rows)}; unique={len(seen)}',flush=True)
    valid=[r for r in rows if r['status']=='ok']; unique=[r for r in valid if not r['duplicate_of']]
    # If same landscape occurs across train/validation, exclude validation copy to avoid leakage.
    train_hashes={r['landscape_hash'] for r in valid if r['partition']=='internal_train'}
    for r in valid:
        r['leakage_safe_validation']=r['partition']=='internal_validation' and r['landscape_hash'] not in train_hashes and not r['duplicate_of']
    payload={'version':'QHDE-v0.29','offline_only':True,'split':'TRAIN only',
      'partition_caveat':'Internal hash partition of audited TRAIN clips, not externally held-out TEST corpus',
      'selection_basis':'Reference harmony, no corrected EMH scores or QAOA outcomes',
      'reference_blind_scoring':True,'no_qpu_jobs_submitted':True,
      'archive_sha256':stable_digest(Path(archive)),'manifest_sha256':stable_digest(Path(manifest)),
      'per_stratum_requested':per_stratum,'selection_metadata':meta,'split_seed':seed,
      'n_candidates':len(rows),'n_valid':len(valid),'n_unique_landscapes':len(unique),
      'n_internal_train':sum(r['partition']=='internal_train' for r in valid),
      'n_internal_validation_clean':sum(r['leakage_safe_validation'] for r in valid),
      'records':rows}
    save(out/'manifest.json',payload)
    fields=['record_id','stratum','partition','status','n_feasible','n_optimal','n_segments','landscape_hash','duplicate_of','leakage_safe_validation','chord_entropy_bits','conditional_transition_entropy_bits','repeated_bigram_rate','file','reason']
    with (out/'instances.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    report=['# QHDE v0.29 — Expanded four-segment benchmark','',
        f'- Audited TRAIN clips in original manifest: **{len(ids)}**',
        f'- Preselected music-only candidates: **{len(selected)}**',
        f'- Valid EMH four-segment problems: **{len(valid)}**',
        f'- Distinct affine-normalized landscapes: **{len(unique)}**',
        f'- Internal training instances: **{payload["n_internal_train"]}**',
        f'- Leak-safe internal validation instances: **{payload["n_internal_validation_clean"]}**',
        '- **No hardware experiment executed; no quantum advantage demonstrated.**','',
        '## Interpretation','',
        '- Each instance contains 4 consecutive melody segments, 4 fixed candidates per segment, 256 possible states.',
        '- All candidates and harmonic scores come from corrected HARMONIX EMH; human harmony is not used for scoring.',
        '- The TRAIN-only internal validation is not equivalent to an independent TEST corpus.',
        '- Duplicate normalized landscapes must be grouped; music clips need not be independent songs.',
        '- Generated tasks are a dataset, NOT optimized QAOA solutions. Use later offline simulation with prespecified budget.',
        '- Full-song reference entropy remains a proxy; temporal note/harmony alignment requires a separate audit.','']
    (out/'REPORT.md').write_text('\n'.join(report),encoding='utf8')
    print('SAVED',out/'manifest.json','unique',len(unique),'NO QPU JOB SUBMITTED')
    return payload

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive');ap.add_argument('--manifest',default=str(DEFAULT_MANIFEST))
    ap.add_argument('--out',default='QHDE/results/expanded_v29')
    ap.add_argument('--per-stratum',type=int,default=100)
    ap.add_argument('--min-chords',type=int,default=8)
    ap.add_argument('--max-records',type=int,default=0,help='Pilot subset, 0=all selected')
    ap.add_argument('--seed',default='QHDE-v29-locked-split')
    a=ap.parse_args()
    if a.per_stratum<1 or a.min_chords<2 or a.max_records<0:ap.error('invalid limits')
    if a.archive:archive=Path(a.archive)
    else:
        sys.path.insert(0,str(ROOT/'HARMONIX'))
        from harmonix.shared_data import require_hooktheory
        archive=Path(require_hooktheory())
    generate(archive,a.manifest,a.out,a.per_stratum,a.min_chords,a.max_records,a.seed)
if __name__=='__main__':main()
