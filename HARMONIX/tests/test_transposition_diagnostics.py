"""v0.19 regression tests for transposition-aware post-generation summaries."""
from harmonix.structural_reference_diagnostics import summarize
from harmonix.rq_final_analysis import analyze

ARMS = ('corrected', 'repetition', 'function', 'combined')
NAMES = ('untransposed_same_reference_root', 'untransposed_changed_reference_root',
         'transposed_reference_tracks_melody', 'transposed_reference_not_tracking_melody')


def test_summary_transposition_strata():
    def counts(n, correct):
        return {'n_pairs': n, 'arms': {arm: {
            'relation_correct': correct, 'both_chords_correct': 0,
            'generated_same_root': 0, 'generated_tracks_melody': 0,
            'generated_matches_reference_interval': correct} for arm in ARMS}}
    row = {'status': 'ok', 'pair_diagnostics': {
        'strata': {'same_reference_root': counts(2, 1),
                   'changed_reference_root': counts(1, 1)},
        'transposition_strata': {name: counts(i, 1 if i else 0)
                                 for i, name in enumerate(NAMES)}}}
    result = summarize([row])
    assert result['transposition_strata'][NAMES[0]]['n_pairs'] == 0
    assert result['transposition_strata'][NAMES[1]]['arms']['corrected']['generated_matches_reference_interval_rate'] == 1
    assert result['transposition_strata'][NAMES[3]]['n_pairs'] == 3


def test_rq_transposition_cluster_bootstrap():
    scores = {arm: {metric: 0.5 for metric in (
        'chord_agreement', 'root_agreement', 'function_agreement',
        'exact_chord_transition', 'repeated_pair_both_correct',
        'repeated_pair_reference_relation')} for arm in ARMS}
    def counts(arm):
        return {'n_pairs': 2, 'arms': {a: {
            'generated_matches_reference_interval': 2 if a == arm else 1,
            'relation_correct': 1} for a in ARMS}}
    row = {'id': 'a', 'status': 'ok', 'scores': scores,
           'pair_diagnostics': {'strata': {
               'same_reference_root': {'n_pairs': 0, 'arms': {a: {'relation_correct': 0} for a in ARMS}},
               'changed_reference_root': {'n_pairs': 0, 'arms': {a: {'relation_correct': 0} for a in ARMS}}},
               'transposition_strata': {name: counts('repetition') for name in NAMES}}}
    manifest = {'split': 'VALID', 'selected': [{'id': 'a', 'artist': 'X', 'song': 'Y'}]}
    result = analyze([row], manifest, repeats=100)
    assert result['transposition_pair_level'][NAMES[2]]['repetition']['difference_percentage_points'] == 50
    assert result['transposition_pair_level'][NAMES[2]]['combined']['difference_percentage_points'] == 0
