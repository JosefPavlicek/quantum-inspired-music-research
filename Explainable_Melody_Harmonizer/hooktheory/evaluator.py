"""Post-hoc evaluation of frozen EMH against HookTheory chord annotations.

Human harmony and annotated keys must never enter the generation path.
Metrics use the dominant reference chord by temporal overlap with each EMH segment.
"""
from fractions import Fraction
from music21 import pitch
import re


def _f(x):
    return Fraction(str(x)).limit_denominator(4096)


def _root(symbol):
    m = re.match(r'^([A-G](?:#|b|-)?)', symbol)
    return pitch.Pitch(m.group(1)).pitchClass if m else None


def _ref_pcs(ref):
    """HookTheory intervals are successive intervals in root position."""
    root = int(ref['root_pitch_class']) % 12
    offsets = [0]
    for step in ref['root_position_intervals']:
        offsets.append((offsets[-1] + int(step)) % 12)
    return frozenset((root + o) % 12 for o in offsets)


def _reference_function(root_pc, candidates):
    """Function implied by diatonic candidate roots; not an independent truth label."""
    labels = {c.function for c in candidates if _root(c.symbol) == root_pc}
    return next(iter(labels)) if len(labels) == 1 else None


def evaluate(decisions, reference, meter, candidates=None):
    candidates = list(candidates or [])
    bar = Fraction(int(meter['beats_per_bar']) * 4, int(meter['beat_unit']))
    out = []
    for d in decisions:
        start = bar * (d.segment.measure - 1) + d.segment.start_beat - 1
        end = start + d.segment.duration
        overlaps = []
        for r in reference:
            overlap = max(Fraction(0), min(end, _f(r['offset'])) - max(start, _f(r['onset'])))
            if overlap > 0:
                overlaps.append((overlap, r))
        if not overlaps:
            out.append({'segment': d.segment.index, 'status': 'no_reference'})
            continue
        weight, human = max(overlaps, key=lambda pair: pair[0])
        human_root = int(human['root_pitch_class']) % 12
        human_pcs = _ref_pcs(human)
        generated_root = _root(d.selected.symbol)
        human_function = _reference_function(human_root, candidates)
        coverage = any(_root(c.symbol) == human_root and c.pitch_classes == human_pcs for c in candidates)
        root_coverage = any(_root(c.symbol) == human_root for c in candidates)
        out.append({
            'segment': d.segment.index, 'status': 'evaluated',
            'human_root_pc': human_root, 'generated_root_pc': generated_root,
            'human_pitch_classes': sorted(human_pcs),
            'generated_pitch_classes': sorted(d.selected.pitch_classes),
            'root_agreement': generated_root == human_root,
            'chord_agreement': generated_root == human_root and d.selected.pitch_classes == human_pcs,
            'candidate_coverage': coverage, 'root_candidate_coverage': root_coverage,
            'human_function': human_function, 'generated_function': d.selected.function,
            'function_agreement': d.selected.function == human_function if human_function is not None else None,
            'reference_coverage_fraction': float(sum(w for w, _ in overlaps) / (end - start)),
            'dominant_reference_fraction': float(weight / (end - start)),
            'mixed_reference': len(overlaps) > 1,
            'human_intervals': human.get('root_position_intervals'),
            'generated_chord': d.selected.symbol,
        })
    valid = [s for s in out if s['status'] == 'evaluated']
    def rate(field):
        values = [s[field] for s in valid if s[field] is not None]
        return sum(values) / len(values) if values else None
    pure = [s for s in valid if not s['mixed_reference']]
    covered = [s for s in valid if s['candidate_coverage']]
    return {'segments': out, 'summary': {
        'total_segments': len(out), 'evaluated_segments': len(valid),
        'root_agreement': rate('root_agreement'),
        'chord_agreement': rate('chord_agreement'),
        'function_agreement': rate('function_agreement'),
        'function_evaluable_segments': sum(s['human_function'] is not None for s in valid),
        'candidate_coverage': rate('candidate_coverage'),
        'root_candidate_coverage': rate('root_candidate_coverage'),
        'chord_agreement_given_coverage': sum(s['chord_agreement'] for s in covered) / len(covered) if covered else None,
        'unmixed_root_agreement': sum(s['root_agreement'] for s in pure) / len(pure) if pure else None,
        'unmixed_segments': len(pure),
        'mixed_reference_segments': sum(s['mixed_reference'] for s in valid),
    }}
