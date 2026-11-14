"""Joint work-proxy cluster bootstrap for 12 context-by-arm contrasts.

Uses v0.19 benchmark JSONL and its matching audited manifest. No generation.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import random
from .rq_final_analysis import ARMS, group_key

CONTEXTS = ('untransposed_same_reference_root',
            'untransposed_changed_reference_root',
            'transposed_reference_tracks_melody',
            'transposed_reference_not_tracking_melody')


def quantile(xs, p):
    ys = sorted(xs)
    index = (len(ys)-1)*p
    lo = int(index)
    hi = min(lo+1, len(ys)-1)
    return ys[lo]*(hi-index)+ys[hi]*(index-lo)


def analyze(rows, manifest, repeats=5000, seed=2027):
    if manifest.get('split') != 'VALID':
        raise ValueError('Multiplicity assessment requires held-out VALID')
    if repeats < 100:
        raise ValueError('At least 100 bootstrap replicates required')
    entries = {x['id']: x for x in manifest['selected']}
    if len(entries) != len(manifest['selected']):
        raise ValueError('Duplicate manifest IDs')
    clusters = defaultdict(lambda: [[0, 0, 0, 0] for _ in range(12)])
    seen = set()
    for row in rows:
        ident = row['id']
        if ident not in entries or ident in seen:
            raise ValueError(f'Unknown or repeated record: {ident}')
        seen.add(ident)
        if row['status'] != 'ok':
            continue
        strata = row['pair_diagnostics']['transposition_strata']
        work = clusters[group_key(entries[ident])]
        for ci, context in enumerate(CONTEXTS):
            bucket = strata[context]
            n = bucket['n_pairs']
            base = bucket['arms']['corrected']['generated_matches_reference_interval']
            for ai, arm in enumerate(ARMS):
                alt = bucket['arms'][arm]['generated_matches_reference_interval']
                slot = work[ci*3+ai]
                slot[0] += alt-base
                slot[1] += n
    if not clusters:
        raise ValueError('No successful records')
    entries_by_work = list(clusters.values())
    def effects(sample):
        numerators = [0]*12
        denominators = [0]*12
        for work in sample:
            for i, (num, den, _, _) in enumerate(work):
                numerators[i] += num
                denominators[i] += den
        return [100*n/d if d else None for n, d in zip(numerators, denominators)]
    observed = effects(entries_by_work)
    if any(v is None for v in observed):
        raise ValueError('One or more contexts have no motif pairs')
    rng = random.Random(seed)
    draws = []
    nworks = len(entries_by_work)
    for _ in range(repeats):
        sample = [entries_by_work[rng.randrange(nworks)] for _ in range(nworks)]
        values = effects(sample)
        if any(v is None for v in values):
            raise ValueError('Empty bootstrap context; consider a larger sample')
        draws.append(values)
    # Max absolute centered error, not an unadjusted marginal percentile CI.
    maxima = [max(abs(draw[i]-observed[i]) for i in range(12)) for draw in draws]
    critical = quantile(maxima, .95)
    contrasts = {}
    for ci, context in enumerate(CONTEXTS):
        contrasts[context] = {}
        for ai, arm in enumerate(ARMS):
            i = ci*3+ai
            contrasts[context][arm] = {
                'effect_pp': observed[i],
                'simultaneous_ci95_pp': [observed[i]-critical, observed[i]+critical],
                'unadjusted_percentile_ci95_pp': [quantile([d[i] for d in draws], .025),
                                                   quantile([d[i] for d in draws], .975)],
                'n_pairs': sum(w[i][1] for w in entries_by_work),
                'n_work_proxy_clusters': sum(w[i][1] > 0 for w in entries_by_work)}
    return {'method': 'joint cluster bootstrap, max absolute centered error, simultaneous 95% intervals',
            'split': 'VALID', 'seed': seed, 'replicates': repeats,
            'work_proxy_clusters': nworks, 'critical_pp': critical,
            'contrasts': contrasts,
            'limitations': ['Artist/song is a proxy work identifier.',
                            'Simultaneous coverage is bootstrap approximate, not an exact guarantee.',
                            'VALID is not an untouched confirmatory sample.']}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results', default='results/structural_reference_valid_v019.jsonl')
    p.add_argument('--manifest', default='results/corpus_manifests/valid_full.json')
    p.add_argument('--output', default='results/structural_multiplicity.json')
    p.add_argument('--bootstrap', type=int, default=5000)
    p.add_argument('--seed', type=int, default=2027)
    args = p.parse_args(argv)
    with open(args.results, encoding='utf8') as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    report = analyze(rows, json.loads(Path(args.manifest).read_text(encoding='utf8')),
                     args.bootstrap, args.seed)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf8')
    print(f'Wrote {output}; {report["work_proxy_clusters"]} work-proxy clusters')


if __name__ == '__main__':
    main()
