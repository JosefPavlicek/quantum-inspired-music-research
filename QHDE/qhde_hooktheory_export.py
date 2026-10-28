"""QHDE v0.4: reference-blind TRAIN HookTheory -> two-segment score tables.

Only READS HARMONIX and the frozen EMH, writes only under QHDE.
Run from repository root: python QHDE/qhde_hooktheory_export.py ...
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
HARMONIX = ROOT / 'HARMONIX'


def choose_ids(manifest, limit):
    if manifest.get('split') != 'TRAIN' or manifest.get('preflight_only') is not True:
        raise ValueError('Only audited preflight TRAIN manifest is supported')
    ids = [entry['id'] for entry in manifest['selected']]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate IDs in manifest')
    return ids[:limit] if limit else ids


def atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def build_env():
    sys.path.insert(0, str(HARMONIX))
    from harmonix.baseline import verify_snapshot
    from harmonix.emh_bridge import VENDOR
    from harmonix.shared_data import require_hooktheory
    verify_snapshot()
    sys.path.insert(0, str(ROOT / 'Explainable_Melody_Harmonizer'))
    sys.path.insert(0, str(VENDOR))
    from hooktheory.loader import melody_only
    from hooktheory.adapter import adapt
    from emh.key_detection import detect_key
    from emh.segmentation import segment_notes
    from emh.model import ChordCandidate
    from emh.scoring import (melody_compatibility, functional_transition,
                             persistence, cadential_score, local_score,
                             segment_has_sounding_notes)
    from harmonix.knowledge_candidates import generate
    from music21.key import Key
    import yaml
    config = yaml.safe_load((VENDOR / 'config.yaml').read_text(encoding='utf-8'))
    scoring = dict(melody_compatibility=melody_compatibility,
                   functional_transition=functional_transition,
                   persistence=persistence, cadential_score=cadential_score,
                   local_score=local_score,
                   segment_has_sounding_notes=segment_has_sounding_notes)
    return locals()


def evaluate_two_prefix_segments(record, env):
    """Local first-two-segment objective; no reference harmony is read."""
    from qhde_harmonix_bridge import pair_scores
    melody = env['adapt'](env['melody_only'](record))
    key = env['detect_key'](melody.notes)
    segments = env['segment_notes'](melody.notes, melody.time_signatures, env['config'])
    if len(segments) < 2:
        raise ValueError('Fewer than two melody segments')
    scale = {p.pitchClass for p in env['Key'](key.tonic, key.mode).pitches}
    # Original v0.3 bridge always treats position 2 as final. This must be
    # corrected for songs with more than 2 segments. Do not silently use it.
    if len(segments) != 2:
        return score_prefix_nonfinal(segments[:2], key, scale, env)
    result = pair_scores(segments[:2], key.tonic, key.mode, scale, env['config'],
                        scoring=env['scoring'], candidate_builder=env['ChordCandidate'])
    result['task'] = 'first_two_segments_full_song'  # second IS final
    result['total_song_segments'] = len(segments)
    return result


def score_prefix_nonfinal(pair, key, scale, env):
    """Same components as EMH optimizer, with is_final=False at both positions."""
    candidates = [env['ChordCandidate'](c.symbol,c.roman,c.pitch_classes,c.function)
                  for c in env['generate'](key.tonic, key.mode, 'corrected')]
    scoring = env['scoring']; config = env['config']; w = (config or {}).get('scoring',{}).get('weights')
    mel = scoring['melody_compatibility']; tr = scoring['functional_transition']
    persistence = scoring['persistence']; cadence = scoring['cadential_score']; local = scoring['local_score']
    sound = scoring['segment_has_sounding_notes']
    rows=[]
    for i,a in enumerate(candidates):
        s0 = local(mel(pair[0],a,scale,config),tr(None,a,config),
                   persistence(None,a,config),cadence(None,a,False,config),w)
        for j,b in enumerate(candidates):
            if not sound(pair[1]) and a.roman != b.roman:
                continue
            s1 = local(mel(pair[1],b,scale,config),tr(a,b,config),
                       persistence(a,b,config),cadence(a,b,False,config),w)
            rows.append(dict(a=a.symbol,a_roman=a.roman,b=b.symbol,b_roman=b.roman,
                             a_index=i,b_index=j,score=float(s0+s1)))
    if not rows: raise ValueError('No valid pairs')
    return dict(model='harmonix_corrected_candidates_frozen_emh_scoring',
                candidate_variant='corrected',tonic=key.tonic,mode=key.mode,
                candidate_count=len(candidates),pair_count=len(rows),segments=2,
                second_segment_is_final=False,total_song_segments=None,
                task='first_two_segments_local_prefix',
                candidate_vocabulary=[dict(symbol=c.symbol,roman=c.roman,function=c.function,
                                           pitch_classes=sorted(c.pitch_classes))
                                      for c in env['generate'](key.tonic,key.mode,'corrected')],
                pairs=rows)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',default=str(HARMONIX/'results/corpus_manifests/train_full.json'))
    parser.add_argument('--archive',help='Override HookTheory archive path')
    parser.add_argument('--limit',type=int,default=5,help='Number of TRAIN records; 0 = all')
    parser.add_argument('--out',default=str(ROOT/'QHDE/results/hooktheory_v04'))
    args=parser.parse_args(argv)
    if args.limit < 0: parser.error('--limit must be >= 0')
    manifest_path=Path(args.manifest)
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    ids=choose_ids(manifest,args.limit)
    env=build_env()
    archive=Path(args.archive) if args.archive else env['require_hooktheory']()
    with gzip.open(archive,'rt',encoding='utf-8') as f:
        dataset=json.load(f)
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    reports=[]
    for i, ident in enumerate(ids):
        try:
            if ident not in dataset: raise KeyError('Record missing from HookTheory archive')
            result=evaluate_two_prefix_segments(dataset[ident],env)
            result['record_id']=ident
            result['source_split']='TRAIN'
            result['source_archive_name']=archive.name
            result['manifest_sha256']=hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            result['total_song_segments']=result.get('total_song_segments') or None
            target=out/f'scores_{i:03d}.json'
            atomic_json(target,result)
            reports.append(dict(id=ident,status='ok',pairs=result['pair_count'],
                                tonic=result['tonic'],mode=result['mode'],file=target.name,
                                task=result['task']))
            print(f'OK {i+1}/{len(ids)}: {ident}, {result["pair_count"]} pairs -> {target}')
        except Exception as exc:
            reports.append(dict(id=ident,status='failed',reason=f'{type(exc).__name__}: {exc}'))
            print(f'FAILED {i+1}/{len(ids)}: {ident}: {exc}',file=sys.stderr)
    atomic_json(out/'summary.json',dict(version='QHDE-v0.4',simulation_only=True,
        reference_blind=True,model='HARMONIX corrected candidates + frozen EMH scoring',
        manifest=str(manifest_path),archive_name=archive.name,rows=reports))
    with (out/'summary.csv').open('w',newline='',encoding='utf-8') as f:
        wr=csv.DictWriter(f,fieldnames=['id','status','pairs','tonic','mode','file','task','reason'])
        wr.writeheader();wr.writerows(reports)
    if not any(r['status']=='ok' for r in reports):
        raise SystemExit('No successful records; check failures above. IBM time NOT used.')
    print('Export complete. No QPU submission was performed.')

if __name__=='__main__': main()
