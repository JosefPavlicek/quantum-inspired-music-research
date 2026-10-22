import pytest
from harmonix.emh_bridge import EMHDecisionGraph
from harmonix.oracle_experiment import evaluate_one_query, exact_agreement, blind_rank


def graph():
    return EMHDecisionGraph({
        "chords": ["I", "V"],
        "segments": [{"measure": i+1, "beat": "1"} for i in range(3)],
        "initial": {"I": 1., "V": 0.},
        "edges": [
            {"I\tI": 1., "I\tV": -3., "V\tI": -3., "V\tV": 1.},
            {"I\tI": 1., "I\tV": -3., "V\tI": -3., "V\tV": 1.},
        ],
    })


def test_perfect_baseline():
    r = evaluate_one_query(graph(), ["I", "I", "I"])
    assert r["baseline_agreement"] == 1
    assert r["selected"]["gain"] == 0
    assert r["random_expected_gain"] == 0


def test_oracle_improvement_and_random_exact_expectation():
    r = evaluate_one_query(graph(), ["V", "V", "V"])
    assert r["baseline_agreement"] == 0
    assert r["selected"]["gain"] == 1
    assert r["random_expected_gain"] == 1
    assert r["advantage_over_uniform_random"] == 0


def test_reference_validation():
    with pytest.raises(ValueError, match="Expected"):
        evaluate_one_query(graph(), ["I"])
    with pytest.raises(ValueError, match="outside"):
        evaluate_one_query(graph(), ["I", "IV", "I"])


def test_reference_does_not_affect_selection():
    assert evaluate_one_query(graph(), ["I","I","I"])["selected_position"] == evaluate_one_query(
        graph(), ["V","V","V"])["selected_position"]


def test_agreement_length():
    with pytest.raises(ValueError):
        exact_agreement(["I"], [])


def test_ranking_is_complete():
    assert sorted(blind_rank(graph())) == [0, 1, 2]
