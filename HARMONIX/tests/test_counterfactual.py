import pytest
from harmonix.counterfactual import SequentialModel, reference_distance, evaluate_intervention


def chain():
    # Local scores favor A at each step; transition rewards staying together.
    return SequentialModel([{'A': 1.0, 'B': 0.0} for _ in range(5)],
                           {('A', 'A'): 3.0, ('B', 'B'): 3.0,
                            ('A', 'B'): -5.0, ('B', 'A'): -5.0})


def test_baseline():
    assert chain().optimize().choices == ('A',) * 5


def test_counterfactual_changes_global_path():
    model = chain()
    cf = model.optimize({2: 'B'})
    assert cf.choices == ('B',) * 5


def test_rank_is_reference_blind():
    model = chain()
    assert model.rank_positions()[0][1] == 5
    assert all(0 <= pos < 5 for pos, _ in model.rank_positions())


def test_gain_can_be_negative():
    model = chain()
    baseline = model.optimize()
    intervention = next(x for x in model.interventions() if x.position == 2)
    result = evaluate_intervention(intervention, baseline, baseline.choices)
    assert result['gain'] == -5
    assert result['influence'] == 5


def test_gain_can_be_positive():
    model = chain()
    baseline = model.optimize()
    intervention = next(x for x in model.interventions() if x.position == 2)
    result = evaluate_intervention(intervention, baseline, ('B',) * 5)
    assert result['gain'] == 5


def test_bad_reference_length():
    with pytest.raises(ValueError):
        reference_distance(('A',), ('A', 'B'))


def test_invalid_constraint():
    with pytest.raises(ValueError):
        chain().optimize({10: 'B'})


def test_impossible_transition():
    model = SequentialModel([{'A': 1}, {'B': 1}], {})
    with pytest.raises(ValueError):
        model.optimize()


def test_deterministic_tie_breaking():
    model = SequentialModel([{'B': 0, 'A': 0}], {})
    assert model.optimize().choices == ('A',)
