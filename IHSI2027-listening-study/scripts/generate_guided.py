#!/usr/bin/env python3
"""IHSI 2027: reference-blind persistence-guided optimization over HARMONIX graphs.

Run from repository root:
  PYTHONPATH=HARMONIX python IHSI2027-listening-study/scripts/generate_guided.py

Uses existing frozen EMH scoring graphs; does not change HARMONIX or EMH.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def optimize_persistence(graph, penalty: float):
    """Viterbi on exact HARMONIX edges, minus penalty per chord change."""
    if penalty < 0:
        raise ValueError('penalty must be nonnegative')
    previous = {c: (float(s), (c,)) for c, s in graph.initial.items()}
    if not previous:
        raise ValueError('No initial states')
    for t, edges in enumerate(graph.edges, 1):
        current = {}
        for c in graph.chords:
            best = None
            for p in graph.chords:
                edge = edges.get(f'{p}\t{c}')
                if edge is None or p not in previous:
                    continue
                prev_score, prev_path = previous[p]
                trial = (prev_score + float(edge) - (penalty if p != c else 0.0), prev_path + (c,))
                if best is None or trial[0] > best[0][0] + 1e-12 or (
                    abs(trial[0] - best[0][0]) <= 1e-12 and graph._priority[p] < graph._priority[best[1]]
                ):
                    best = (trial, p)
            if best is not None:
                current[c] = best[0]
        if not current:
            raise ValueError(f'No feasible path at segment {t}')
        previous = current
    winner = None
    winner_chord = None
    for c in graph.chords:
        if c not in previous:
            continue
        trial = previous[c]
        if winner is None or trial[0] > winner[0] + 1e-12 or (
            abs(trial[0] - winner[0]) <= 1e-12 and graph._priority[c] < graph._priority[winner_chord]
        ):
            winner, winner_chord = trial, c
    return winner


def raw_emh_score(graph, path):
    score = float(graph.initial[path[0]])
    for t in range(1, len(path)):
        score += float(graph.edges[t - 1][f'{path[t-1]}\t{path[t]}'])
    return score


def n_changes(path):
    return sum(a != b for a, b in zip(path, path[1:]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, default=Path('IHSI2027-listening-study/experiments/pilot_corpus/manifest.json'))
    ap.add_argument('--dataset', type=Path, default=Path('data/Hooktheory.json.gz'))
    ap.add_argument('--harmonix', type=Path, default=Path('HARMONIX'))
    ap.add_argument('--penalty', type=float, default=0.15, help='Exploratory change penalty in native EMH score units')
    args = ap.parse_args()
    if args.penalty <= 0:
        ap.error('--penalty must be positive')
    manifest_path, dataset, harmonix = (p.resolve() for p in (args.manifest, args.dataset, args.harmonix))
    sys.path.insert(0, str(harmonix))
    from harmonix.baseline import verify_snapshot
    from harmonix.emh_bridge import EMHDecisionGraph
    verify_snapshot()
    vendor = harmonix / 'vendor' / 'emh_baseline'
    worker = harmonix / 'harmonix' / '_hooktheory_worker.py'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    failures = 0
    for clip in manifest['clips']:
        clip_id, ident = clip['clip_id'], clip['hooktheory_record_id']
        output = manifest_path.parent / clip_id / 'guided_emh.json'
        print(f'{clip_id}: ', end='', flush=True)
        try:
            baseline_path = output.parent / 'baseline_emh.json'
            baseline_report = json.loads(baseline_path.read_text(encoding='utf-8'))
            if baseline_report['hooktheory_record_id'] != ident:
                raise ValueError('Baseline record ID mismatch')
            proc = subprocess.run([sys.executable, str(worker), str(dataset), ident], cwd=vendor, check=True, capture_output=True, text=True)
            data = json.loads(proc.stdout)
            if data.get('id') != ident:
                raise ValueError('Worker record ID mismatch')
            graph = EMHDecisionGraph(data)
            baseline = graph.optimize()
            if list(baseline.choices) != data['emh_baseline'] or list(baseline.choices) != baseline_report['emh_baseline']:
                raise ValueError('Baseline parity mismatch')
            # Verify the new optimizer is identical to baseline when preference weight = 0.
            zero_score, zero_path = optimize_persistence(graph, 0.0)
            if list(zero_path) != list(baseline.choices) or abs(zero_score - baseline.score) > 1e-8:
                raise ValueError('Zero-penalty parity failed')
            objective, guided_path = optimize_persistence(graph, args.penalty)
            guided_score = raw_emh_score(graph, guided_path)
            report = {
                'clip_id': clip_id, 'hooktheory_record_id': ident,
                'method': 'HARMONIX EMH scoring graph + explicit chord-change penalty',
                'preference': {'name': 'harmonic_persistence', 'change_penalty': args.penalty,
                               'units': 'native EMH graph score per chord change', 'status': 'exploratory_not_calibrated'},
                'baseline_emh': list(baseline.choices), 'guided_emh': list(guided_path),
                'n_segments': len(graph.segments), 'segments': list(graph.segments),
                'detected_key': data.get('detected_key'),
                'baseline_emh_score': baseline.score, 'guided_emh_score': guided_score,
                'guided_objective': objective, 'emh_score_difference': guided_score - baseline.score,
                'baseline_chord_changes': n_changes(baseline.choices),
                'guided_chord_changes': n_changes(guided_path),
                'changed_segment_positions': [i for i, (a, b) in enumerate(zip(baseline.choices, guided_path)) if a != b],
                'baseline_parity': True, 'zero_penalty_parity': True,
                'reference_used_for_generation': False,
                'worker_sha256': hashlib.sha256(worker.read_bytes()).hexdigest(),
                'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            }
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(f'OK changes {report["baseline_chord_changes"]}->{report["guided_chord_changes"]}, modified segments {len(report["changed_segment_positions"])}')
        except Exception as exc:
            failures += 1
            print(f'FAILED {exc}')
            if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
                print(exc.stderr[-2000:], file=sys.stderr)
    print(f'Completed: {len(manifest["clips"]) - failures}/{len(manifest["clips"])}')
    return int(failures > 0)


if __name__ == '__main__':
    raise SystemExit(main())
