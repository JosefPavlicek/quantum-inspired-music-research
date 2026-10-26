"""v0.19 reference-aware, generation-blind repeated-motif diagnostics.

Re-runs the four existing models, without modifying their generation logic.
References are accessed only after generation. TRAIN and VALID; no TEST.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import time

from .structural_benchmark import ARMS, _initialize, _run_record


def summarize(rows):
    result = {'n_rows': len(rows), 'statuses': dict(Counter(r['status'] for r in rows)),
              'strata': {}, 'notes': [
                  'Reference ROOT equality, not proof of intentional reharmonization.',
                  'Motif links are those of structural_links, not human-annotated phrases.',
                  'Descriptive pair-weighted counts; correlated pairs and repeated works.',
                  'Exploratory TRAIN or VALID; reference is not available to the generator.']}
    for stratum in ('same_reference_root', 'changed_reference_root'):
        n = 0
        counts = {arm: Counter() for arm in ARMS}
        for row in rows:
            if row['status'] != 'ok':
                continue
            block = row['pair_diagnostics']['strata'][stratum]
            n += block['n_pairs']
            for arm in ARMS:
                counts[arm].update(block['arms'][arm])
        result['strata'][stratum] = {'n_pairs': n, 'arms': {
            arm: {**dict(counts[arm]), **{k + '_rate': (counts[arm][k] / n if n else None)
                         for k in ('relation_correct', 'both_chords_correct', 'generated_same_root')}}
            for arm in ARMS}}
    if any('transposition_strata' in r.get('pair_diagnostics', {}) for r in rows if r['status'] == 'ok'):
        result['transposition_strata'] = {}
        names = ('untransposed_same_reference_root',
                 'untransposed_changed_reference_root',
                 'transposed_reference_tracks_melody',
                 'transposed_reference_not_tracking_melody')
        for name in names:
            n = 0
            counts = {arm: Counter() for arm in ARMS}
            for row in rows:
                if row['status'] != 'ok':
                    continue
                block = row['pair_diagnostics']['transposition_strata'][name]
                n += block['n_pairs']
                for arm in ARMS:
                    counts[arm].update(block['arms'][arm])
            result['transposition_strata'][name] = {'n_pairs': n, 'arms': {
                arm: {**dict(counts[arm]), **{k + '_rate': counts[arm][k] / n if n else None
                        for k in ('relation_correct', 'both_chords_correct',
                                  'generated_same_root', 'generated_tracks_melody',
                                  'generated_matches_reference_interval')}}
                for arm in ARMS}}
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--summary', required=True)
    p.add_argument('--archive')
    p.add_argument('--limit', type=int, default=50, help='0 = all selected records')
    p.add_argument('--iterations', type=int, default=4)
    p.add_argument('--progress-every', type=int, default=100)
    args = p.parse_args(argv)
    if args.limit < 0 or args.iterations < 1 or args.progress_every < 1:
        p.error('Invalid numerical argument')
    manifest = json.loads(Path(args.manifest).read_text(encoding='utf8'))
    if manifest.get('split') not in ('TRAIN', 'VALID') or manifest.get('preflight_only') is not True:
        p.error('Requires preflight TRAIN or VALID manifest (TEST excluded)')
    ids = [item['id'] for item in manifest['selected']]
    if len(ids) != len(set(ids)):
        p.error('Duplicate manifest IDs')
    if args.limit:
        ids = ids[:args.limit]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    settings = {'split': manifest['split'], 'ids': ids, 'iterations': args.iterations, 'arms': ARMS, 'version': 'v0.19'}
    sidecar = out.with_suffix(out.suffix + '.settings.json')
    if sidecar.exists():
        if json.loads(sidecar.read_text(encoding='utf8')) != json.loads(json.dumps(settings)):
            raise ValueError('Resume settings mismatch; use a new output')
    elif out.exists() and out.stat().st_size:
        raise ValueError('Output exists without settings; use a new output')
    else:
        sidecar.write_text(json.dumps(settings), encoding='utf8')
    prior = {}
    if out.exists():
        for line in out.read_text(encoding='utf8').splitlines():
            if line.strip():
                row = json.loads(line)
                if row['id'] in prior or row['id'] not in ids:
                    raise ValueError('Duplicate/unexpected prior ID')
                prior[row['id']] = row
    env = _initialize()
    archive = Path(args.archive) if args.archive else env['require_hooktheory']()
    with gzip.open(archive, 'rt', encoding='utf8') as f:
        dataset = json.load(f)
    start = time.monotonic()
    with out.open('a', encoding='utf8') as f:
        for i, ident in enumerate(ids, 1):
            if ident not in prior:
                result = (_run_record(dataset[ident], env, ARMS, args.iterations, pair_diagnostics=True)
                          if ident in dataset else {'status': 'failed', 'reason': 'Missing record'})
                row = {'id': ident, 'split': manifest['split'], **result}
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
                f.flush()
                prior[ident] = row
            if i % args.progress_every == 0:
                print(f'{i}/{len(ids)} elapsed={time.monotonic()-start:.1f}s', flush=True)
    report = {'version': 'v0.19', 'split': manifest['split'], 'parameters': settings,
              'summary': summarize([prior[i] for i in ids])}
    Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
    Path(args.summary).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report['summary'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
