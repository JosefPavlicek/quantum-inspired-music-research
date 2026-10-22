import pytest
from harmonix.emh_bridge import EMHDecisionGraph


def graph():
    return EMHDecisionGraph({
        'chords': ['I', 'V'],
        'segments': [{'measure': i + 1, 'beat': '1'} for i in range(3)],
        'initial': {'I': 1.0, 'V': 0.0},
        'edges': [
            {'I\tI': 1, 'I\tV': -3, 'V\tI': -3, 'V\tV': 1},
            {'I\tI': 1, 'I\tV': -3, 'V\tI': -3, 'V\tV': 1},
        ]
    })


def test_unconstrained():
    assert graph().optimize().choices == ('I', 'I', 'I')


def test_forcing_reoptimizes_globally():
    assert graph().optimize({1: 'V'}).choices == ('V', 'V', 'V')


def test_influence():
    result = [i for i in graph().interventions() if i.position == 1 and i.forced == 'V'][0]
    assert result.changed_positions == (0, 1, 2)
    assert result.influence == 3
    assert result.score_loss >= 0


def test_reference_not_required():
    assert graph().rank_positions()[0][1] == 3


def test_invalid_forcing():
    with pytest.raises(ValueError):
        graph().optimize({0: 'not-a-chord'})


def test_rest_transition_constraint():
    data = {'chords': ['I', 'V'], 'segments': [{'measure': 1, 'beat': '1'}, {'measure': 1, 'beat': '3'}],
            'initial': {'I': 1.0, 'V': 0.0}, 'edges': [{'I\tI': 1, 'V\tV': 1}]}
    assert EMHDecisionGraph(data).optimize({1: 'V'}).choices == ('V', 'V')


def test_bad_graph_dimensions():
    with pytest.raises(ValueError):
        EMHDecisionGraph({'chords': ['I'], 'segments': [{'measure': 1}], 'initial': {'I': 1}, 'edges': [{}]})
