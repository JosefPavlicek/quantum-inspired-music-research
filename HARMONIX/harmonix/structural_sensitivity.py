"""Reference-blind sensitivity grid using the existing HARMONIX optimizer.

Each weight pair is a full reoptimization; no scoring of frozen chord paths.
TRAIN is the default; VALID must be explicitly requested and not used for tuning.
"""
import argparse
import gzip
import json
from pathlib import Path
import sys
import time
from .structural_benchmark import _initialize, _run_record

GRID_R = (0.06, 0.12, 0.18)
GRID_F = (0.03, 0.06, 0.09)


def weights_for(r, f):
    if r < 0 or f < 0:
        raise ValueError('Weights must be nonnegative')
    return {'repetition': (r, 0.0), 'function': (0.0, f), 'combined': (r, f)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', default='results/corpus_manifests/train_full.json')
    p.add_argument('--archive', help='HookTheory gzip archive; default uses configured data path')
    p.add_argument('--output-dir', default='results/structural_sensitivity')
    p.add_argument('--limit', type=int, default=100, help='First N records; 0 = all')
    p.add_argument('--iterations', type=int, default=4)
    p.add_argument('--progress-every', type=int, default=25)
    p.add_argument('--allow-valid', action='store_true', help='Explicit VALID confirmation, no tuning')
    args = p.parse_args(argv)
    if args.limit < 0 or args.iterations < 1 or args.progress_every < 1:
        p.error('Invalid numeric argument')
    manifest = json.loads(Path(args.manifest).read_text(encoding='utf8'))
    split = manifest.get('split')
    if not manifest.get('preflight_only') or split not in ('TRAIN', 'VALID'):
        p.error('Expected audited TRAIN/VALID preflight manifest')
    if split == 'VALID' and not args.allow_valid:
        p.error('VALID requires --allow-valid; do not tune on validation')
    ids = [r['id'] for r in manifest['selected']]
    if len(set(ids)) != len(ids):
        p.error('Duplicate manifest IDs')
    if args.limit:
        ids = ids[:args.limit]
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    env = _initialize()
    archive = Path(args.archive) if args.archive else env['require_hooktheory']()
    with gzip.open(archive, 'rt', encoding='utf8') as stream:
        dataset = json.load(stream)
    for r in GRID_R:
        for f in GRID_F:
            weights = weights_for(r, f)
            stem = f'{split.lower()}_r{r:.2f}_f{f:.2f}'
            dest = outdir / f'{stem}.jsonl'
            settings = {'split': split, 'ids': ids, 'weights': weights,
                        'iterations': args.iterations, 'model': 'structural_sensitivity_v1',
                        'pair_diagnostics': True}
            sidecar = dest.with_suffix(dest.suffix+'.settings.json')
            if sidecar.exists():
                if json.loads(sidecar.read_text(encoding='utf8')) != json.loads(json.dumps(settings)):
                    raise ValueError(f'Resume settings mismatch: {dest}')
            elif dest.exists() and dest.stat().st_size:
                raise ValueError(f'Output without settings: {dest}')
            else:
                sidecar.write_text(json.dumps(settings, indent=2)+'\n', encoding='utf8')
            previous = {}
            if dest.exists():
                for line in dest.read_text(encoding='utf8').splitlines():
                    if line.strip():
                        row = json.loads(line)
                        if row['id'] in previous or row['id'] not in ids:
                            raise ValueError(f'Unexpected/duplicate resume ID: {row["id"]}')
                        previous[row['id']] = row
            start = time.monotonic()
            with dest.open('a', encoding='utf8') as stream:
                for index, ident in enumerate(ids, 1):
                    if ident not in previous:
                        result = (_run_record(dataset[ident], env, weights, args.iterations,
                                              pair_diagnostics=True)
                                  if ident in dataset else {'status': 'failed', 'reason': 'Missing record'})
                        stream.write(json.dumps({'id': ident, 'split': split, **result},
                                                ensure_ascii=False)+'\n')
                        stream.flush()
                    if index % args.progress_every == 0:
                        print(f'{stem}: {index}/{len(ids)} ({time.monotonic()-start:.0f}s)', flush=True)
            print(f'Finished {dest}', flush=True)
    print('Grid completed. Analyze each JSONL with rq_final_analysis using the same manifest.')


if __name__ == '__main__':
    main()
