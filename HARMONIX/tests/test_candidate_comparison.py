from harmonix.candidate_comparison import summarize


def test_summary_uses_clean_denominator_and_preserves_failures():
    rows = [{'status': 'ok', 'metrics': {
        name: {'clean': 4, 'covered': c, 'selected': s, 'segments': 6}
        for name, c, s in [('baseline', 2, 1), ('corrected', 3, 2), ('extended', 4, 3)]
    }}, {'status': 'failed', 'id': 'x', 'error': 'meter'}]
    result = summarize(rows)
    assert result['n_requested'] == 2
    assert result['n_evaluated'] == 1
    assert result['n_failed'] == 1
    assert result['variants']['baseline']['coverage_rate_clean'] == 0.5
    assert result['variants']['extended']['selection_rate_clean'] == 0.75


def test_zero_clean_has_no_division_by_zero():
    rows = [{'status': 'ok', 'metrics': {
        name: {'clean': 0, 'covered': 0, 'selected': 0, 'segments': 2}
        for name in ('baseline', 'corrected', 'extended')
    }}]
    assert summarize(rows)['variants']['baseline']['coverage_rate_clean'] is None
