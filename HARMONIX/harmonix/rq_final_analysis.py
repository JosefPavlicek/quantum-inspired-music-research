"""v0.18: final exploratory/validation RQ analysis; never changes generation."""
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
STRATA = ('same_reference_root', 'changed_reference_root')


def group_key(item):
    artist = ' '.join(str(item.get('artist') or '').casefold().split())
    song = ' '.join(str(item.get('song') or '').casefold().split())
    return f'work:{artist}\x1f{song}' if artist and song else f"record:{item['id']}"


def interval(values):
    values.sort()
    return [values[int(.025 * (len(values) - 1))], values[int(.975 * (len(values) - 1))]]


def bootstrap_clusters(clusters, repeats, seed):
    """Cluster-weighted ratio-of-sums, resampling musical works."""
    if not clusters:
        return None
    rng = random.Random(seed)
    entries = list(clusters.values())
    observed = sum(a for a, _ in entries) / sum(b for _, b in entries)
    draws = []
    for _ in range(repeats):
        selected = [entries[rng.randrange(len(entries))] for _ in entries]
        draws.append(sum(a for a, _ in selected) / sum(b for _, b in selected))
    return {'estimate': observed, 'ci95': interval(draws), 'n_clusters': len(entries)}


def analyze(rows, manifest, repeats=1000, seed=2027):
    if manifest.get('split') not in ('TRAIN', 'VALID'):
        raise ValueError('Only TRAIN or VALID are permitted')
    entries = {item['id']: item for item in manifest['selected']}
    if len(entries) != len(manifest['selected']):
        raise ValueError('Duplicate manifest IDs')
    seen = set()
    grouped = defaultdict(list)
    statuses = Counter()
    for row in rows:
        ident = row['id']
        if ident in seen or ident not in entries:
            raise ValueError(f'Duplicate or unexpected record ID: {ident}')
        seen.add(ident)
        statuses[row['status']] += 1
        if row['status'] == 'ok':
            grouped[group_key(entries[ident])].append(row)
    result = {'split': manifest['split'], 'n_records': len(rows),
              'n_successful': sum(map(len, grouped.values())),
              'n_work_proxy_clusters': len(grouped), 'statuses': dict(statuses),
              'bootstrap_replicates': repeats, 'seed': seed,
              'record_level': {}, 'motif_pair_level': {},
              'limitations': [
                  'Artist/song is a proxy for musical work, not an independently verified identifier.',
                  'Pairs and records are correlated; intervals resample work-proxy clusters.',
                  'Reference root equality does not establish intentional reharmonization.',
                  'TRAIN is exploratory; VALID is validation, not a pristine confirmatory holdout.',
                  'No multiple-comparison adjustment; all results are descriptive/exploratory.']}
    for metric in METRICS:
        result['record_level'][metric] = {}
        for ai, arm in enumerate(ARMS):
            clusters = {}
            outcomes = Counter()
            for key, work_rows in grouped.items():
                deltas = []
                for row in work_rows:
                    b = row['scores']['corrected'].get(metric)
                    x = row['scores'][arm].get(metric)
                    if b is None or x is None:
                        continue
                    d = x - b
                    deltas.append(d)
                    outcomes['improved' if d > 1e-12 else 'worsened' if d < -1e-12 else 'unchanged'] += 1
                if deltas:
                    clusters[key] = (sum(deltas), len(deltas))
            stats = bootstrap_clusters(clusters, repeats, seed + 100 * METRICS.index(metric) + ai)
            result['record_level'][metric][arm] = ({'difference_percentage_points': stats['estimate'] * 100,
                 'ci95_percentage_points': [v * 100 for v in stats['ci95']],
                 'n_work_proxy_clusters': stats['n_clusters'],
                 'n_records': sum(v[1] for v in clusters.values()),
                 'outcomes': dict(outcomes)} if stats else None)
    if any('pair_diagnostics' in r for work in grouped.values() for r in work):
        for si, stratum in enumerate(STRATA):
            result['motif_pair_level'][stratum] = {}
            for ai, arm in enumerate(ARMS):
                clusters = {}
                baseline_count = alternative_count = total_pairs = 0
                for key, work_rows in grouped.items():
                    diff = denom = 0
                    for row in work_rows:
                        diag = row.get('pair_diagnostics')
                        if not diag:
                            continue
                        bucket = diag['strata'][stratum]
                        n = bucket['n_pairs']
                        base = bucket['arms']['corrected']['relation_correct']
                        alt = bucket['arms'][arm]['relation_correct']
                        diff += alt - base
                        denom += n
                        baseline_count += base
                        alternative_count += alt
                        total_pairs += n
                    if denom:
                        clusters[key] = (diff, denom)
                stats = bootstrap_clusters(clusters, repeats, seed + 500 + si * 10 + ai)
                result['motif_pair_level'][stratum][arm] = ({
                    'n_pairs': total_pairs, 'n_work_proxy_clusters': stats['n_clusters'],
                    'corrected_rate': baseline_count / total_pairs,
                    'arm_rate': alternative_count / total_pairs,
                    'difference_percentage_points': stats['estimate'] * 100,
                    'ci95_percentage_points': [v * 100 for v in stats['ci95']]
                } if stats else None)
    trans_names = ('untransposed_same_reference_root',
                   'untransposed_changed_reference_root',
                   'transposed_reference_tracks_melody',
                   'transposed_reference_not_tracking_melody')
    if any('transposition_strata' in r.get('pair_diagnostics', {})
           for work in grouped.values() for r in work):
        result['transposition_pair_level'] = {}
        for si, stratum in enumerate(trans_names):
            result['transposition_pair_level'][stratum] = {}
            for ai, arm in enumerate(ARMS):
                clusters = {}
                total = base_total = alt_total = 0
                for key, work_rows in grouped.items():
                    diff = denom = 0
                    for row in work_rows:
                        diag = row.get('pair_diagnostics', {})
                        if 'transposition_strata' not in diag:
                            continue
                        bucket = diag['transposition_strata'][stratum]
                        n = bucket['n_pairs']
                        b = bucket['arms']['corrected']['generated_matches_reference_interval']
                        x = bucket['arms'][arm]['generated_matches_reference_interval']
                        diff += x - b
                        denom += n
                        total += n
                        base_total += b
                        alt_total += x
                    if denom:
                        clusters[key] = (diff, denom)
                stats = bootstrap_clusters(clusters, repeats, seed + 1000 + si * 10 + ai)
                result['transposition_pair_level'][stratum][arm] = ({
                    'metric': 'generated_matches_reference_interval',
                    'n_pairs': total, 'n_work_proxy_clusters': stats['n_clusters'],
                    'corrected_rate': base_total / total,
                    'arm_rate': alt_total / total,
                    'difference_percentage_points': stats['estimate'] * 100,
                    'ci95_percentage_points': [v * 100 for v in stats['ci95']]}
                    if stats else None)
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results', required=True)
    p.add_argument('--manifest', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--bootstrap', type=int, default=1000)
    p.add_argument('--seed', type=int, default=2027)
    args = p.parse_args(argv)
    if args.bootstrap < 100:
        p.error('bootstrap must be >=100')
    manifest = json.loads(Path(args.manifest).read_text(encoding='utf8'))
    with Path(args.results).open(encoding='utf8') as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    report = analyze(rows, manifest, args.bootstrap, args.seed)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(f"{report['split']}: {report['n_successful']}/{report['n_records']} successful, "
          f"{report['n_work_proxy_clusters']} work-proxy clusters; wrote {path}")


if __name__ == '__main__':
    main()
