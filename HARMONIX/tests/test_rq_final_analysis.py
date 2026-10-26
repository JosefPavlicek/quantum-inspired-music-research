import pytest
from harmonix.rq_final_analysis import analyze


def row(ident, reference_same, base_correct, arm_correct):
    metrics = ('chord_agreement', 'root_agreement', 'function_agreement',
               'exact_chord_transition', 'repeated_pair_both_correct',
               'repeated_pair_reference_relation')
    scores = {arm: {m: .2 for m in metrics} for arm in ('corrected', 'repetition', 'function', 'combined')}
    return {'id': ident, 'status': 'ok', 'scores': scores,
            'pair_diagnostics': {'strata': {
                name: {'n_pairs': 1 if name == reference_same else 0,
                       'arms': {arm: {'relation_correct': val if name == reference_same else 0}
                                for arm, val in [('corrected', base_correct),
                                                 ('repetition', arm_correct),
                                                 ('function', base_correct),
                                                 ('combined', arm_correct)]}}
                for name in ('same_reference_root', 'changed_reference_root')}}}


def test_stratified_pair_analysis():
    manifest = {'split': 'TRAIN', 'selected': [{'id': 'a', 'artist': 'A', 'song': 'S'},
                                              {'id': 'b', 'artist': 'B', 'song': 'T'}]}
    result = analyze([row('a', 'same_reference_root', 0, 1),
                      row('b', 'changed_reference_root', 1, 0)], manifest, repeats=100)
    same = result['motif_pair_level']['same_reference_root']['repetition']
    changed = result['motif_pair_level']['changed_reference_root']['repetition']
    assert same['difference_percentage_points'] == 100
    assert changed['difference_percentage_points'] == -100
    assert result['n_work_proxy_clusters'] == 2


def test_valid_allowed_test_rejected():
    manifest = {'split': 'VALID', 'selected': [{'id': 'a'}]}
    assert analyze([row('a', 'same_reference_root', 1, 1)], manifest, repeats=100)['split'] == 'VALID'
    with pytest.raises(ValueError):
        analyze([], {'split': 'TEST', 'selected': []}, repeats=100)
