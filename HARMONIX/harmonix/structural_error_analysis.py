"""Paired, song-clustered exploratory analysis of v0.15 results.

Reference-aware analysis occurs only after harmonization. No generation here.
"""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import random

ARMS = ('repetition', 'function', 'combined')
METRICS = ('chord_agreement', 'root_agreement', 'function_agreement',
           'exact_chord_transition', 'repeated_pair_both_correct',
           'repeated_pair_reference_relation')


def group_key(item):
    artist = ' '.join(str(item.get('artist') or '').casefold().split())
    song = ' '.join(str(item.get('song') or '').casefold().split())
    if artist and song:
        return f'work:{artist}\x1f{song}'
    return f"record:{item['id']}"  # no unsafe merging of missing metadata


def analyze(rows, manifest, bootstrap=1000, seed=2027):
    if manifest.get('split') != 'TRAIN':
        raise ValueError('v0.16 analysis restricted to exploratory TRAIN')
    entries = {item['id']: item for item in manifest['selected']}
    seen = set()
    grouped = defaultdict(list)
    statuses = Counter()
    for row in rows:
        ident = row['id']
        if ident in seen:
            raise ValueError(f'duplicate ID: {ident}')
        seen.add(ident)
        if ident not in entries:
            raise ValueError(f'ID not in manifest: {ident}')
        statuses[row['status']] += 1
        if row['status'] == 'ok':
            grouped[group_key(entries[ident])].append(row)
    rng = random.Random(seed)
    keys = sorted(grouped)
    output = {'split': 'TRAIN', 'n_rows': len(seen), 'n_successful': sum(map(len, grouped.values())),
              'n_song_proxy_clusters': len(keys), 'statuses': dict(statuses),
              'bootstrap_replicates': bootstrap, 'seed': seed, 'metrics': {},
              'limitations': [
                  'Artist/song metadata are an imperfect proxy for independent musical works.',
                  'TRAIN exploratory analysis only, not confirmatory inference.',
                  'Reference-relation metric checks equality of reference and generated ROOT-repeat relations; it does not identify composer intent or reharmonization causes.',
                  'A v0.15 JSONL stores aggregate rates, not individual repeated-pair reference labels. It cannot stratify same-reference vs changed-reference motif pairs.',
                  'Confidence intervals are percentile cluster bootstrap intervals for mean record-level paired differences; not adjusted for multiple comparisons.'
              ]}
    for metric in METRICS:
        result = {}
        for arm in ARMS:
            # Each cluster is an independent resampling unit, while records within
            # each selected cluster retain their original within-cluster weighting.
            cluster_sums = []
            all_deltas = []
            wins = Counter()
            for key in keys:
                vals = []
                for row in grouped[key]:
                    base = row['scores']['corrected'].get(metric)
                    alternative = row['scores'][arm].get(metric)
                    if base is None or alternative is None:
                        continue
                    delta = alternative - base
                    vals.append(delta)
                    all_deltas.append(delta)
                    wins['improved' if delta > 1e-12 else 'worsened' if delta < -1e-12 else 'unchanged'] += 1
                if vals:
                    cluster_sums.append((sum(vals), len(vals)))
            if not all_deltas:
                result[arm] = {'n_records': 0}
                continue
            observed = sum(all_deltas) / len(all_deltas)
            draws = []
            n = len(cluster_sums)
            for _ in range(bootstrap):
                numerator = denominator = 0
                for _ in range(n):
                    subtotal, count = cluster_sums[rng.randrange(n)]
                    numerator += subtotal
                    denominator += count
                draws.append(numerator / denominator)
            draws.sort()
            result[arm] = {
                'n_records': len(all_deltas), 'n_clusters': n,
                'mean_paired_difference': observed,
                'mean_difference_percentage_points': observed * 100,
                'cluster_bootstrap_ci95_percentage_points': [
                    draws[int(0.025 * bootstrap)] * 100,
                    draws[min(bootstrap - 1, math.ceil(0.975 * bootstrap) - 1)] * 100
                ],
                'record_outcomes': dict(wins)
            }
        output['metrics'][metric] = result
    return output


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results', required=True, help='v0.15 per-record JSONL')
    p.add_argument('--manifest', required=True, help='TRAIN manifest with artist/song')
    p.add_argument('--output', required=True)
    p.add_argument('--bootstrap', type=int, default=1000)
    p.add_argument('--seed', type=int, default=2027)
    args = p.parse_args(argv)
    if args.bootstrap < 100:
        p.error('--bootstrap must be >= 100')
    manifest = json.loads(Path(args.manifest).read_text(encoding='utf8'))
    with Path(args.results).open(encoding='utf8') as stream:
        rows = (json.loads(line) for line in stream if line.strip())
        report = analyze(rows, manifest, args.bootstrap, args.seed)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(f"Analyzed {report['n_successful']} successful records in {report['n_song_proxy_clusters']} clusters")
    for metric in ('chord_agreement', 'repeated_pair_reference_relation'):
        for arm in ARMS:
            v = report['metrics'][metric][arm]
            print(f"{metric} / {arm}: {v['mean_difference_percentage_points']:+.3f} pp, CI95 {v['cluster_bootstrap_ci95_percentage_points']}")


if __name__ == '__main__':
    main()
