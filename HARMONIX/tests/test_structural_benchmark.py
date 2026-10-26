from harmonix.structural_benchmark import _rates, _summary


def test_metrics_reference_pairs():
    evaluation = {'segments': [
        {'status': 'evaluated', 'chord_agreement': True, 'root_agreement': True,
         'function_agreement': True, 'human_root_pc': 0, 'generated_root_pc': 0},
        {'status': 'no_reference'},
        {'status': 'evaluated', 'chord_agreement': False, 'root_agreement': False,
         'function_agreement': None, 'human_root_pc': 0, 'generated_root_pc': 7}]}
    result = _rates(evaluation, [(0, 2)])
    assert result['chord_agreement'] == .5
    assert result['repeated_pair_both_correct'] == 0
    assert result['repeated_pair_reference_relation'] == 0
    assert result['n_transitions_evaluable'] == 0


def test_summary_song_level_not_segment_pooled():
    scores = {arm: {'chord_agreement': value, 'root_agreement': value,
                    'function_agreement': None, 'exact_chord_transition': None,
                    'repeated_pair_both_correct': None,
                    'repeated_pair_reference_relation': None}
              for arm, value in [('corrected', .5), ('repetition', .75),
                                 ('function', .5), ('combined', 1.)]}
    report = _summary([{'status': 'ok', 'scores': scores}], 1)
    assert report['arms']['combined']['chord_agreement']['mean_per_record'] == 1
    assert report['arms']['corrected']['chord_agreement']['n_records'] == 1
