#!/usr/bin/env python3
"""Generate reference-blind HARMONIX/EMH baselines for an IHSI pilot manifest.
Run from repository root with: PYTHONPATH=HARMONIX python IHSI2027-listening-study/scripts/generate_baselines.py
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('IHSI2027-listening-study/experiments/pilot_corpus/manifest.json'))
    parser.add_argument('--dataset', type=Path, default=Path('data/Hooktheory.json.gz'))
    parser.add_argument('--harmonix', type=Path, default=Path('HARMONIX'))
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    dataset = args.dataset.resolve()
    harmonix = args.harmonix.resolve()
    if not manifest_path.is_file() or not dataset.is_file():
        parser.error('Manifest or HookTheory dataset missing')
    sys.path.insert(0, str(harmonix))
    from harmonix.baseline import verify_snapshot
    from harmonix.emh_bridge import EMHDecisionGraph
    verify_snapshot()
    vendor = harmonix / 'vendor' / 'emh_baseline'
    worker = harmonix / 'harmonix' / '_hooktheory_worker.py'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    clips = manifest.get('clips')
    if not isinstance(clips, list) or not clips:
        parser.error('Expected nonempty manifest.clips array')
    failures = 0
    for clip in clips:
        clip_id = clip['clip_id']
        ident = clip['hooktheory_record_id']
        output_dir = manifest_path.parent / clip_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / 'baseline_emh.json'
        print(f'{clip_id} ({ident}): ', end='', flush=True)
        try:
            proc = subprocess.run([sys.executable, str(worker), str(dataset), ident], cwd=vendor, capture_output=True, text=True, check=True)
            data = json.loads(proc.stdout)
            if data.get('id') != ident:
                raise ValueError('Worker returned mismatched HookTheory ID')
            graph = EMHDecisionGraph(data)
            result = graph.optimize()
            parity = list(result.choices) == data['emh_baseline']
            if not parity:
                raise ValueError('EMH parity check FAILED')
            report = {
                'clip_id': clip_id,
                'hooktheory_record_id': ident,
                'source': 'HookTheory melody-only via frozen EMH graph',
                'emh_baseline': list(result.choices),
                'baseline_score': result.score,
                'n_segments': len(graph.segments),
                'segments': list(graph.segments),
                'candidate_chords': list(graph.chords),
                'detected_key': data.get('detected_key'),
                'parity_with_emh': True,
                'reference_used_for_generation': False,
            }
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(f'OK: {len(result.choices)} segments -> {output}')
        except Exception as exc:
            failures += 1
            print(f'FAILED: {exc}')
            if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
                print(exc.stderr[-2000:], file=sys.stderr)
    print(f'Completed: {len(clips) - failures}/{len(clips)}')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
