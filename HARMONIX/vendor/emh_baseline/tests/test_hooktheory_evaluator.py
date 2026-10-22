from fractions import Fraction
from emh.model import HarmonicSegment, ChordCandidate, Decision, ScoreComponents
from hooktheory.evaluator import evaluate, _ref_pcs


def test_interval_steps_not_absolute_offsets():
    assert _ref_pcs({'root_pitch_class': 0, 'root_position_intervals': [4, 3]}) == frozenset({0, 4, 7})


def test_metrics_and_coverage():
    c = ChordCandidate('C', 'I', frozenset({0, 4, 7}), 'tonic')
    d = Decision(HarmonicSegment(0, 1, Fraction(1), Fraction(2)), c, ScoreComponents())
    ref = [{'onset': 0, 'offset': 2, 'root_pitch_class': 0, 'root_position_intervals': [4, 3]}]
    result = evaluate([d], ref, {'beats_per_bar': 4, 'beat_unit': 4}, [c])
    s = result['segments'][0]
    assert s['root_agreement'] and s['chord_agreement'] and s['candidate_coverage']
    assert s['function_agreement'] is True


def test_function_not_evaluable_when_reference_root_outside_candidates():
    c = ChordCandidate('C', 'I', frozenset({0, 4, 7}), 'tonic')
    d = Decision(HarmonicSegment(0, 1, Fraction(1), Fraction(2)), c, ScoreComponents())
    ref = [{'onset': 0, 'offset': 2, 'root_pitch_class': 1, 'root_position_intervals': [4, 3]}]
    s = evaluate([d], ref, {'beats_per_bar': 4, 'beat_unit': 4}, [c])['segments'][0]
    assert s['function_agreement'] is None and not s['candidate_coverage']
