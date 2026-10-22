"""Private worker: read frozen EMH modules, emit reference-blind scoring graph."""
from __future__ import annotations
import json
import sys
from pathlib import Path

VENDOR = Path.cwd()
sys.path.insert(0, str(VENDOR))

from music21 import key as m21key
import yaml
from emh.musicxml_loader import load_musicxml
from emh.key_detection import detect_key
from emh.segmentation import segment_notes
from emh.harmony import generate_candidates
from emh.optimizer import optimize
from emh.scoring import (melody_compatibility, functional_transition, persistence,
                         cadential_score, local_score, segment_has_sounding_notes)


def extract(path):
    config = yaml.safe_load((VENDOR / 'config.yaml').read_text(encoding='utf-8'))
    melody = load_musicxml(path)
    detected = detect_key(melody.notes)
    key = m21key.Key(detected.tonic, detected.mode)
    segments = segment_notes(melody.notes, melody.time_signatures, config)
    candidates = generate_candidates(detected.tonic, detected.mode, config)
    scale = {p.pitchClass for p in key.pitches}
    weights = config.get('scoring', {}).get('weights')
    ids = [c.roman for c in candidates]
    if len(set(ids)) != len(ids):
        raise ValueError('Frozen EMH has duplicate candidate identifiers')
    if not segments:
        raise ValueError('No harmonic segments')
    first = {}
    edges = []
    for t, seg in enumerate(segments):
        final = t == len(segments) - 1
        for c in candidates:
            m = melody_compatibility(seg, c, scale, config)
            if t == 0:
                first[c.roman] = local_score(m, functional_transition(None, c, config),
                                             persistence(None, c, config),
                                             cadential_score(None, c, final, config), weights)
        if t == 0:
            continue
        row = {}
        rest_only = not segment_has_sounding_notes(seg)
        for p in candidates:
            for c in candidates:
                if rest_only and p.roman != c.roman:
                    continue
                m = melody_compatibility(seg, c, scale, config)
                f = functional_transition(p, c, config)
                persist = persistence(p, c, config)
                cad = cadential_score(p, c, final, config)
                row[f'{p.roman}\t{c.roman}'] = local_score(m, f, persist, cad, weights)
        edges.append(row)
    original = optimize(segments, candidates, scale, config)
    return {'chords': ids, 'segments': [{'index': s.index, 'measure': s.measure,
                                        'beat': str(s.start_beat), 'duration': str(s.duration)}
                                       for s in segments],
            'initial': first, 'edges': edges,
            'detected_key': detected.name,
            'emh_baseline': [d.selected.roman for d in original]}


if __name__ == '__main__':
    print(json.dumps(extract(sys.argv[1]), ensure_ascii=False))
