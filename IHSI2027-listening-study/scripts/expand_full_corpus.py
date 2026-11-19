#!/usr/bin/env python3
"""Expand selected HookTheory records into full annotated excerpts, without truncation.

Reads IDs from pilot_corpus/manifest.json. Writes a separate full_corpus tree.
Does NOT modify the pilot corpus or generate new harmonizations.
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from prepare_corpus import xml_melody


def read_json(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as f:
        return json.load(f)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', default='data/Hooktheory.json.gz')
    p.add_argument('--pilot', default='IHSI2027-listening-study/experiments/pilot_corpus')
    p.add_argument('--output', default='IHSI2027-listening-study/experiments/full_corpus')
    args = p.parse_args()
    pilot = Path(args.pilot)
    output = Path(args.output)
    manifest = read_json(pilot / 'manifest.json')
    dataset = read_json(Path(args.dataset))
    if output.resolve() == pilot.resolve():
        raise SystemExit('Output must differ from pilot corpus')
    output.mkdir(parents=True, exist_ok=True)
    result = []
    for entry in manifest['clips']:
        cid = entry['clip_id']
        rid = entry['hooktheory_record_id']
        rec = dataset[rid]
        ann = rec['annotations']
        melody = sorted(ann.get('melody') or [], key=lambda n: (float(n['onset']), float(n['offset'])))
        harmony = sorted(ann.get('harmony') or [], key=lambda n: (float(n['onset']), float(n['offset'])))
        if not melody or not harmony:
            raise ValueError(f'{cid}: missing melody or harmony')
        annotated_end = max(max(float(n['offset']) for n in melody), max(float(h['offset']) for h in harmony))
        declared_end = float(ann.get('num_beats') or 0)
        beats = max(annotated_end, declared_end)
        if beats <= 0:
            raise ValueError(f'{cid}: invalid duration')
        folder = output / cid
        folder.mkdir(parents=True, exist_ok=True)
        xml_melody(melody, folder / 'melody.musicxml', beats=beats)
        (folder / 'reference_harmony.json').write_text(json.dumps(harmony, indent=2, ensure_ascii=False), encoding='utf-8')
        metadata = {
            'clip_id': cid, 'hooktheory_record_id': rid,
            'pilot_beats': entry.get('beats'), 'full_beats': beats,
            'annotated_end_beats': annotated_end, 'declared_num_beats': declared_end,
            'melody_events': len(melody), 'harmony_events': len(harmony),
            'detected_or_declared_meter': ann.get('meters'),
            'note': 'Full available HookTheory annotation, not necessarily full commercial song; audio not rendered yet.'
        }
        (folder / 'metadata.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
        result.append(metadata)
        bpm = float(entry.get('bpm_rendered') or 100)
        print(f"{cid} ({rid}): {entry.get('beats')} -> {beats:g} beats; melody {len(melody)}, harmony {len(harmony)}; approx {beats * 60 / bpm:.1f}s at {bpm:g} BPM")
    (output / 'manifest.json').write_text(json.dumps({'source_pilot': str(pilot), 'dataset': str(args.dataset), 'clips': result}, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Completed: {len(result)}/{len(manifest["clips"])}; output: {output}')
    print('No audio or HARMONIX output generated. Verify graph duration before regeneration.')


if __name__ == '__main__':
    main()
