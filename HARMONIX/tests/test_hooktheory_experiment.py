import pytest
from harmonix.emh_bridge import EMHDecisionGraph
from harmonix.hooktheory_experiment import evaluate_graph

def graph():
    return EMHDecisionGraph({
        'chords':['I','V'],
        'segments':[{'measure':i+1,'beat':'1'} for i in range(3)],
        'initial':{'I':1.,'V':0.},
        'edges':[{'I\tI':1.,'I\tV':-3.,'V\tI':-3.,'V\tV':1.}]*2,
    })

def test_identical_reference():
    result=evaluate_graph(graph(),['I','I','I'])
    assert result['baseline_agreement']==1
    assert result['chosen_gain']==0

def test_full_reference_shift():
    result=evaluate_graph(graph(),['V','V','V'])
    assert result['baseline_agreement']==0
    assert result['chosen_gain']==1
    assert result['random_expected_gain']==1

def test_uncovered_reference():
    result=evaluate_graph(graph(),[None,'I',None])
    assert result['covered_segments']==1

def test_no_coverage():
    with pytest.raises(ValueError,match='No fully aligned'):
        evaluate_graph(graph(),[None,None,None])
