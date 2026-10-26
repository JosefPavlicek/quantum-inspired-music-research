"""Isolated corpus worker. Reference labels are loaded only after generating all paths."""
import json
import sys
from fractions import Fraction
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[1] / 'vendor' / 'emh_baseline'
ROOT = Path(__file__).resolve().parents[2]
LEGACY_EMH = ROOT / 'Explainable_Melody_Harmonizer'
# Frozen EMH supplies the harmonizer; original EMH supplies only the HookTheory adapter.
# The dataset archive itself is resolved independently from root/data/hooktheory.
sys.path.insert(0, str(LEGACY_EMH))
sys.path.insert(0, str(VENDOR))
sys.path.insert(0, str(ROOT / 'HARMONIX'))
from hooktheory.loader import load_dataset, melody_only, reference_only
from hooktheory.adapter import adapt
from emh.key_detection import detect_key
from emh.harmony import generate_candidates
from emh.segmentation import segment_notes
from emh.optimizer import optimize
from emh.model import ChordCandidate
from music21 import key as m21key, pitch
from harmonix.knowledge_candidates import generate
import yaml


def f(x):
    return Fraction(str(x)).limit_denominator(4096)


def root_of(symbol):
    import re
    match = re.match(r'^([A-G](?:#|b|-)?)', symbol)
    if not match:
        raise ValueError('Unparseable candidate symbol: ' + symbol)
    return pitch.Pitch(match.group(1)).pitchClass


def reference_for_segment(seg, harmony, bar):
    start = bar * (seg.measure - 1) + f(seg.start_beat) - 1
    end = start + f(seg.duration)
    overlaps = []
    for chord in harmony:
        w = max(Fraction(0), min(end, f(chord['offset'])) - max(start, f(chord['onset'])))
        if w:
            overlaps.append((w, chord))
    if not overlaps:
        return None, 'no_reference'
    if len(overlaps) != 1 or overlaps[0][0] != end - start:
        return None, 'mixed_or_partial'
    ref = overlaps[0][1]
    root = int(ref['root_pitch_class']) % 12
    offsets = {0}
    cursor = 0
    for step in ref['root_position_intervals']:
        cursor = (cursor + int(step)) % 12
        offsets.add(cursor)
    return (root, frozenset((root + v) % 12 for v in offsets)), 'clean'


def evaluate(segments, candidates, decisions, references):
    if len(segments) != len(decisions) or len(segments) != len(references):
        raise ValueError('Misaligned segments, decisions, or references')
    covered = 0
    selected = 0
    clean = 0
    for decision, (ref, status) in zip(decisions, references):
        if status != 'clean':
            continue
        clean += 1
        root, pcs = ref
        covered += any(root_of(c.symbol) == root and c.pitch_classes == pcs for c in candidates)
        selected += (root_of(decision.selected.symbol) == root and decision.selected.pitch_classes == pcs)
    return {'clean': clean, 'covered': covered, 'selected': selected,
            'candidate_count': len(candidates), 'segments': len(segments)}


def main():
    archive, ident = sys.argv[1:3]
    record = load_dataset(archive)[ident]
    melody = adapt(melody_only(record))
    config = yaml.safe_load((VENDOR / 'config.yaml').read_text(encoding='utf8'))
    detected = detect_key(melody.notes)
    segments = segment_notes(melody.notes, melody.time_signatures, config)
    scale = {p.pitchClass for p in m21key.Key(detected.tonic, detected.mode).pitches}
    variants = {'baseline': generate_candidates(detected.tonic, detected.mode, config)}
    for variant in ('corrected', 'extended'):
        variants[variant] = [ChordCandidate(c.symbol, c.roman, c.pitch_classes, c.function)
                             for c in generate(detected.tonic, detected.mode, variant)]
    # No human reference data has been loaded yet. Freeze generated paths first.
    outputs = {}
    for name, candidates in variants.items():
        if len({c.roman for c in candidates}) != len(candidates):
            raise ValueError(f'Duplicate roman identifiers in {name}')
        decisions = optimize(segments, candidates, scale, config)
        outputs[name] = (candidates, decisions)
    harmony = reference_only(record)
    meter = record['annotations']['meters'][0]
    bar = Fraction(int(meter['beats_per_bar']) * 4, int(meter['beat_unit']))
    refs = [reference_for_segment(s, harmony, bar) for s in segments]
    metrics = {name: evaluate(segments, cand, dec, refs)
               for name, (cand, dec) in outputs.items()}
    print(json.dumps({'id': ident, 'split': record.get('split'),
                      'detected_key': {'tonic': detected.tonic, 'mode': detected.mode},
                      'metrics': metrics, 'reference_status':
                      {status: sum(s == status for _, s in refs)
                       for status in ('clean', 'mixed_or_partial', 'no_reference')}}))


if __name__ == '__main__':
    main()
