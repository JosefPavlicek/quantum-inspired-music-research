#!/usr/bin/env python3
"""Piano-like deterministic pilot WAV synthesizer, drop-in replacement for export_audio.py.

No external dependencies. Keeps render(record, path, bpm=100, sample_rate=22050).
All three listening conditions must be regenerated with the same version.
"""
import argparse
import gzip
import json
import math
import struct
import wave
from pathlib import Path

TAU = 2.0 * math.pi


def render(record, path, bpm=100, sample_rate=22050):
    ann = record['annotations']
    notes = []
    for n in ann['melody']:
        notes.append((float(n['onset']), float(n['offset']), 60 + int(n['pitch_class']), 0.19, True))
    for h in ann['harmony']:
        root = int(h['root_pitch_class'])
        pcs = [root]
        acc = root
        for interval in h['root_position_intervals']:
            acc += int(interval)
            pcs.append(acc % 12)
        inv = int(h.get('inversion', 0)) % len(pcs)
        mids = [48 + pc for pc in pcs]
        for i in range(inv):
            mids[i] += 12
        for midi in mids:
            notes.append((float(h['onset']), float(h['offset']), midi, 0.048, False))

    beats_to_seconds = 60.0 / bpm
    duration = max((n[1] for n in notes), default=0) * beats_to_seconds + 0.4
    size = int(duration * sample_rate)
    samples = [0.0] * size
    # Piano approximation: sharp hammer attack, partials, exponential decay,
    # short key-release, plus brief low-amplitude detuned partials.
    for start, end, midi, volume, is_melody in notes:
        a = max(0, int(start * beats_to_seconds * sample_rate))
        key_end = min(size, int(end * beats_to_seconds * sample_rate))
        tail = min(size, key_end + int(0.16 * sample_rate))
        if a >= tail:
            continue
        freq = 440.0 * 2 ** ((midi - 69) / 12.0)
        # Melody sustains slightly longer; accompaniment is more percussive.
        decay = 1.45 if is_melody else 2.35
        # Frequencies and relative strengths of a small set of piano-like partials.
        partials = ((1.0, 1.0), (2.002, 0.36), (3.008, 0.15), (4.018, 0.07))
        for i in range(a, tail):
            t = (i - a) / sample_rate
            attack = min(1.0, t / 0.004)
            body = math.exp(-decay * t)
            if i >= key_end:
                release = math.exp(-24.0 * (i - key_end) / sample_rate)
            else:
                release = 1.0
            tone = 0.0
            for ratio, amplitude in partials:
                tone += amplitude * math.sin(TAU * freq * ratio * t) * math.exp(-0.36 * (ratio - 1) * t)
            # Gentle hammer transient without random noise, fully deterministic.
            hammer = 0.055 * math.sin(TAU * min(freq * 7.3, sample_rate * 0.43) * t) * math.exp(-55.0 * t)
            samples[i] += volume * attack * body * release * (tone + hammer)

    peak = max((abs(x) for x in samples), default=0.0)
    scale = min(1.0, 0.85 / peak) if peak else 1.0
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        for offset in range(0, size, 4096):
            chunk = samples[offset:offset + 4096]
            writer.writeframesraw(struct.pack('<' + 'h' * len(chunk), *(
                int(max(-1.0, min(1.0, x * scale)) * 32767) for x in chunk
            )))
    return len(ann['melody']), len(ann['harmony'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--id')
    parser.add_argument('--output', default='public/audio/pilot_reference.wav')
    parser.add_argument('--bpm', type=float, default=100)
    args = parser.parse_args()
    with (gzip.open(args.dataset, 'rt', encoding='utf8') if args.dataset.endswith('.gz')
          else open(args.dataset, encoding='utf8')) as handle:
        data = json.load(handle)
    if args.id:
        rid, record = args.id, data[args.id]
    else:
        rid, record = next((k, v) for k, v in data.items()
                           if v.get('annotations', {}).get('melody')
                           and v.get('annotations', {}).get('harmony'))
    n, h = render(record, Path(args.output), bpm=args.bpm)
    print(f'ID={rid}, melody_notes={n}, harmony_events={h}, output={args.output}')
    print('Pilot piano-like synthesis, not a sampled acoustic piano; verify voicing and licensing.')


if __name__ == '__main__':
    main()
