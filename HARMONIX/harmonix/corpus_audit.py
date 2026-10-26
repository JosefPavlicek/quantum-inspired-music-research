"""Read-only, full-corpus HookTheory audit and deterministic per-split manifests.

Does not generate harmonies or access reference chords for model decisions.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path

SUPPORTED = {(2, 4), (3, 4), (4, 4)}

def inspect_record(record):
    a = record.get('annotations') or {}
    meters = a.get('meters') or []
    melody = a.get('melody') or []
    harmony = a.get('harmony') or []
    if not melody or not harmony:
        return 'missing_melody_or_harmony'
    if len(meters) != 1 or meters[0].get('beat') != 0:
        return 'changing_or_missing_meter'
    meter = meters[0]
    if (meter.get('beats_per_bar'), meter.get('beat_unit')) not in SUPPORTED:
        return 'unsupported_meter'
    if not a.get('num_beats'):
        return 'missing_duration'
    return 'eligible_preflight'

def record_label(record):
    # Metadata names are for grouping only, never a unique-work guarantee.
    meta = record.get('hooktheory') or {}
    return (str(meta.get('artist') or record.get('artist') or ''),
            str(meta.get('song') or record.get('song') or ''))

def audit(dataset, seed='HARMONIX-full-corpus-v1'):
    counts = Counter()
    split_counts = defaultdict(Counter)
    manifests = defaultdict(list)
    groups = defaultdict(list)
    for ident, record in dataset.items():
        split = str(record.get('split') or 'UNKNOWN').upper()
        status = inspect_record(record)
        counts[status] += 1
        split_counts[split][status] += 1
        if status == 'eligible_preflight':
            artist, song = record_label(record)
            groups[(artist, song)].append((split, ident))
            rank = hashlib.sha256(f'{seed}:{ident}'.encode()).hexdigest()
            manifests[split].append({'id': ident, 'rank': rank, 'artist': artist, 'song': song})
    duplicates = {f'{artist} / {song}': len(items) for (artist,song),items in groups.items()
                  if artist and song and len(items) > 1}
    cross_split = {f'{artist} / {song}': sorted({split for split,_ in items})
                   for (artist,song),items in groups.items()
                   if artist and song and len({split for split,_ in items}) > 1}
    for rows in manifests.values():
        rows.sort(key=lambda r: (r['rank'], r['id']))
    return {
        'dataset_records': len(dataset),
        'status_counts': dict(sorted(counts.items())),
        'by_split': {k: dict(sorted(v.items())) for k,v in sorted(split_counts.items())},
        'eligible_by_split': {k:len(v) for k,v in sorted(manifests.items())},
        'repeated_artist_song_groups':len(duplicates),
        'repeated_artist_song_records':sum(duplicates.values()),
        'cross_split_artist_song_groups':len(cross_split),
        'cross_split_examples':dict(list(sorted(cross_split.items()))[:30]),
        'warnings':[
            'Preflight eligibility is not verified EMH processing success.',
            'Artist/song metadata are imperfect proxies for unique works or composers.',
            'Existing TEST has been inspected and is exploratory; do not claim unbiased confirmation.',
            'Full-corpus size is not effective independent sample size.'
        ]
    }, manifests

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', help='Path to Hooktheory.json.gz (default: shared dataset)')
    p.add_argument('--output', default='results/corpus_audit.json')
    p.add_argument('--manifest-dir', default='results/corpus_manifests')
    p.add_argument('--seed', default='HARMONIX-full-corpus-v1')
    args=p.parse_args(argv)
    if args.archive:
        archive=Path(args.archive)
    else:
        from .shared_data import require_hooktheory
        archive=require_hooktheory()
    with gzip.open(archive,'rt',encoding='utf8') as f:
        data=json.load(f)
    report, manifests=audit(data,args.seed)
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    directory=Path(args.manifest_dir)
    directory.mkdir(parents=True,exist_ok=True)
    for split, rows in sorted(manifests.items()):
        manifest={'dataset':'SheetSage Hooktheory.json.gz', 'split':split,
                  'seed':args.seed, 'selection_method':'SHA256(seed:record_id)',
                  'requested':len(rows),'eligible':len(rows),
                  'preflight_only':True, 'selected':rows}
        (directory/f'{split.lower()}_full.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=='__main__':
    main()
