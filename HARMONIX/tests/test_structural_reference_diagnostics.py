from harmonix.structural_reference_diagnostics import summarize


def test_reference_strata_and_rates():
    rows = [{'status': 'ok', 'pair_diagnostics': {'strata': {
        'same_reference_root': {'n_pairs': 2, 'arms': {
            arm: {'relation_correct': 1, 'both_chords_correct': 0, 'generated_same_root': 1}
            for arm in ('corrected', 'repetition', 'function', 'combined')}},
        'changed_reference_root': {'n_pairs': 1, 'arms': {
            arm: {'relation_correct': 1, 'both_chords_correct': 1, 'generated_same_root': 0}
            for arm in ('corrected', 'repetition', 'function', 'combined')}}}}}]
    s = summarize(rows)
    assert s['strata']['same_reference_root']['arms']['corrected']['relation_correct_rate'] == .5
    assert s['strata']['changed_reference_root']['arms']['combined']['relation_correct_rate'] == 1
    assert s['strata']['same_reference_root']['n_pairs'] == 2
