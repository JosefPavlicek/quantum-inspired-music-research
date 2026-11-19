#!/usr/bin/env python3
"""Render matched HUMAN/BASELINE/GUIDED WAVs for the IHSI 2027 pilot.

Run from repository root:
  python IHSI2027-listening-study/scripts/render_variants.py

Requires music21 for interpreting EMH Roman-numeral chord labels.
Uses the existing export_audio.render() synthesizer unchanged.
Outputs three *new* WAV files per clip, leaving reference.wav intact.
"""
from __future__ import annotations
import argparse
import gzip
import json
import math
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from export_audio import render
from prepare_corpus import trim

try:
    from music21 import key as m21key, roman as m21roman
except ImportError as exc:
    raise SystemExit('Install music21 in this environment: python -m pip install music21') from exc


def load_json(path):
    path = Path(path)
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8') as handle:
        return json.load(handle)


def chord_annotation(symbol, key_label, start, end):
    parts = key_label.strip().split()
    if len(parts) != 2 or parts[1].lower() not in ('major', 'minor'):
        raise ValueError(f'Unrecognized detected_key: {key_label!r}')
    k = m21key.Key(parts[0], parts[1].lower())
    rn = m21roman.RomanNumeral(symbol, k)
    root_pc = rn.root().pitchClass
    pcs = sorted({p.pitchClass for p in rn.pitches}, key=lambda p: (p - root_pc) % 12)
    if not pcs or pcs[0] != root_pc:
        raise ValueError(f'Could not derive root-position pitches for {symbol} in {key_label}')
    # HookTheory intervals are successive intervals between root-position chord tones.
    offsets = sorted((pc - root_pc) % 12 for pc in pcs)
    intervals = [offsets[i] - offsets[i - 1] for i in range(1, len(offsets))]
    return {'onset': start, 'offset': end, 'root_pitch_class': root_pc,
            'root_position_intervals': intervals, 'inversion': 0}


def build_harmony(data, field, beats, meter=4):
    choices = data[field]
    segments = data['segments']
    if len(choices) != len(segments):
        raise ValueError(f'{field}: {len(choices)} chords but {len(segments)} segments')
    events = []
    for symbol, seg in zip(choices, segments):
        start = (int(seg['measure']) - 1) * meter + float(seg['beat']) - 1
        end = start + float(seg['duration'])
        if end <= 0 or start >= beats:
            continue
        start, end = max(0.0, start), min(float(beats), end)
        if end <= start:
            continue
        if events and start < events[-1]['offset'] - 1e-6:
            raise ValueError(f'Overlapping segments at {start}')
        if events and abs(start - events[-1]['offset']) < 1e-6 and symbol == events[-1]['symbol']:
            events[-1]['offset'] = end
        else:
            events.append({'symbol': symbol, 'onset': start, 'offset': end})
    if not events:
        raise ValueError('No harmony segments in excerpt')
    if events[0]['onset'] > 1e-6 or events[-1]['offset'] < beats - 1e-6:
        raise ValueError(f'Harmony does not cover entire {beats}-beat excerpt: '
                         f'{events[0]["onset"]} to {events[-1]["offset"]}')
    if any(b['onset'] > a['offset'] + 1e-6 for a, b in zip(events, events[1:])):
        raise ValueError('Gap in harmony timeline')
    return [chord_annotation(ev['symbol'], data['detected_key'], ev['onset'], ev['offset'])
            for ev in events]


def normalize_duration(path, beats, bpm, rate=22050):
    """Pad/truncate to the same fixed sample count, without changing sound levels."""
    with wave.open(str(path), 'rb') as reader:
        params = reader.getparams()
        raw = reader.readframes(reader.getnframes())
    if params.nchannels != 1 or params.sampwidth != 2 or params.framerate != rate:
        raise ValueError(f'Unexpected WAV format in {path}')
    target = int((beats * 60 / bpm + 0.4) * rate)
    raw = raw[:target * 2].ljust(target * 2, b'\0')
    with wave.open(str(path), 'wb') as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(raw)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset', default='data/Hooktheory.json.gz')
    ap.add_argument('--corpus', default='IHSI2027-listening-study/experiments/pilot_corpus')
    args = ap.parse_args()
    corpus = Path(args.corpus)
    manifest = load_json(corpus / 'manifest.json')
    dataset = load_json(args.dataset)
    completed = 0
    for item in manifest['clips']:
        cid, rid = item['clip_id'], item['hooktheory_record_id']
        folder = corpus / cid
        try:
            record = dataset[rid]
            beats = float(item['beats'])
            bpm = float(item['bpm_rendered'])
            if bpm <= 0 or beats <= 0:
                raise ValueError('Invalid BPM or excerpt length')
            ann = record['annotations']
            meter = ann['meters'][0]
            if int(meter['beats_per_bar']) != 4 or int(meter['beat_unit']) != 4:
                raise ValueError('Only 4/4 excerpts supported by this pilot')
            melody = trim(ann['melody'], beats)
            reference = trim(ann['harmony'], beats)
            baseline = load_json(folder / 'baseline_emh.json')
            guided = load_json(folder / 'guided_emh.json')
            for obj in (baseline, guided):
                if obj['hooktheory_record_id'] != rid or obj['clip_id'] != cid:
                    raise ValueError('Mismatched clip ID / HookTheory ID')
            if baseline.get('parity_with_emh') is not True:
                raise ValueError('Baseline parity not verified')
            if guided.get('baseline_parity') is not True or guided.get('zero_penalty_parity') is not True:
                raise ValueError('Guided parity not verified')
            if baseline['emh_baseline'] != guided['baseline_emh']:
                raise ValueError('Baseline and guided use different baseline paths')
            for label, harmony in (
                ('human', reference),
                ('baseline', build_harmony(baseline, 'emh_baseline', beats)),
                ('guided', build_harmony(guided, 'guided_emh', beats)),
            ):
                output = folder / f'{label}_matched.wav'
                render({'annotations': {'melody': melody, 'harmony': harmony}}, output, bpm=bpm)
                normalize_duration(output, beats, bpm)
            print(f'{cid}: OK (HUMAN / BASELINE / GUIDED; {beats:g} beats, {bpm:g} BPM)')
            completed += 1
        except Exception as exc:
            print(f'{cid}: FAILED: {exc}', file=sys.stderr)
    print(f'Completed: {completed}/{len(manifest["clips"])}')
    if completed != len(manifest['clips']):
        raise SystemExit(1)
    print('Pilot note: normalized melody register, synthetic voicing, and HookTheory rights still require review.')


if __name__ == '__main__':
    main()
