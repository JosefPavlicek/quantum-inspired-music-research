"""Resumable, reference-blind corrected EMH processing validation over an audited manifest.

Run from HARMONIX. The frozen EMH and original HookTheory adapter are imported
without modification. Uses HARMONIX corrected chord candidates; validates harmonization, not merely preflight.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import sys
import time


def validate_manifest(manifest):
    if manifest.get('preflight_only') is not True:
        raise ValueError('Expected a preflight corpus manifest')
    if manifest.get('split') not in ('TRAIN','VALID','TEST'):
        raise ValueError('Unexpected split')
    ids=[r['id'] for r in manifest['selected']]
    if len(ids)!=len(set(ids)):
        raise ValueError('Duplicate record identifiers')
    return ids


def summarize(rows, requested):
    counts=Counter(row['status'] for row in rows)
    reasons=Counter(row.get('reason','') for row in rows if row['status']!='ok')
    return {'requested':requested,'processed':len(rows),'remaining':requested-len(rows),
            'status_counts':dict(sorted(counts.items())),
            'failure_reasons':dict(sorted(reasons.items())),
            'model':'corrected_emh_via_harmonix', 'note':'Corrected candidate generation without reference harmony; validation only, not an RQ result.'}


def process_record(record, config, adapter, loader, detector, segmentation, candidate_gen, optimizer, key_class):
    try:
        melody=adapter(loader(record))
        detected=detector(melody.notes)
        segments=segmentation(melody.notes,melody.time_signatures,config)
        candidates=candidate_gen(detected.tonic,detected.mode,config)
        scale={p.pitchClass for p in key_class(detected.tonic,detected.mode).pitches}
        decisions=optimizer(segments,candidates,scale,config)
        if not segments or len(decisions)!=len(segments):
            raise ValueError('Invalid or empty optimization result')
        return {'status':'ok','n_segments':len(segments),'n_candidates':len(candidates),
                'detected_mode':detected.mode}
    except Exception as exc:
        return {'status':'failed','reason':type(exc).__name__+': '+str(exc)[:240]}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True)
    p.add_argument('--output',required=True,help='Append-only JSONL result file (resume safe)')
    p.add_argument('--summary',required=True)
    p.add_argument('--archive',help='Override shared HookTheory archive')
    p.add_argument('--limit',type=int,default=0,help='0 = all records')
    p.add_argument('--progress-every',type=int,default=100)
    p.add_argument('--allow-exploratory-test',action='store_true')
    args=p.parse_args(argv)
    if args.limit<0 or args.progress_every<1:p.error('Invalid limit/progress')
    manifest=json.loads(Path(args.manifest).read_text(encoding='utf8'))
    ids=validate_manifest(manifest)
    if manifest['split']=='TEST' and not args.allow_exploratory_test:
        p.error('Inspected TEST requires --allow-exploratory-test')
    if args.limit: ids=ids[:args.limit]
    from .baseline import verify_snapshot
    from .shared_data import require_hooktheory
    from .emh_bridge import VENDOR
    verify_snapshot()
    root=Path(__file__).resolve().parents[2]
    legacy=root/'Explainable_Melody_Harmonizer'
    sys.path.insert(0,str(legacy))
    sys.path.insert(0,str(VENDOR))
    from hooktheory.loader import melody_only
    from hooktheory.adapter import adapt
    from emh.key_detection import detect_key
    from emh.segmentation import segment_notes
    from emh.model import ChordCandidate
    from .knowledge_candidates import generate as knowledge_generate
    def generate_candidates(tonic, mode, config):
        return [ChordCandidate(c.symbol, c.roman, c.pitch_classes, c.function)
                for c in knowledge_generate(tonic, mode, 'corrected')]
    from emh.optimizer import optimize
    from music21.key import Key
    import yaml
    config=yaml.safe_load((VENDOR/'config.yaml').read_text(encoding='utf8'))
    archive=Path(args.archive) if args.archive else require_hooktheory()
    with gzip.open(archive,'rt',encoding='utf8') as f: dataset=json.load(f)
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists() and output.stat().st_size:
        raise ValueError('Output file already exists. Use a NEW corrected-model output path; old v0.13 results cannot be resumed safely.')
    previous={}
    if output.exists():
        for line in output.read_text(encoding='utf8').splitlines():
            if line.strip():
                row=json.loads(line)
                if row['id'] in previous: raise ValueError('Duplicate ID in prior output')
                previous[row['id']]=row
        unexpected=set(previous)-set(ids)
        if unexpected:raise ValueError('Existing output has IDs outside requested manifest/limit')
    start=time.monotonic()
    with output.open('a',encoding='utf8') as f:
        for index,ident in enumerate(ids,1):
            if ident in previous:continue
            if ident not in dataset:
                result={'status':'failed','reason':'Missing record in archive'}
            else:
                result=process_record(dataset[ident],config,adapt,melody_only,detect_key,
                                      segment_notes,generate_candidates,optimize,Key)
            row={'id':ident,'split':manifest['split'],**result}
            f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
            previous[ident]=row
            if index%args.progress_every==0:
                print(f'{index}/{len(ids)} processed; elapsed {time.monotonic()-start:.1f}s',flush=True)
    report={'split':manifest['split'],'exploratory':manifest['split']=='TEST',
            'model':'corrected_emh_via_harmonix',
            'summary':summarize([previous[i] for i in ids if i in previous],len(ids)),
            'warning':'Original TEST has already been inspected; do not use as independent confirmation.'}
    target=Path(args.summary);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
