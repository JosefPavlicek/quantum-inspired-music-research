from harmonix.structural_preservation import metrics, evaluate, summarize
from harmonix.emh_bridge import HarmonicPath

class FakeGraph:
    segments=({}, {}, {})
    chords=('I','V')
    def optimize(self, forced=None):
        forced=forced or {}
        base=['I','I','I']
        for i,c in forced.items():base[i]=c
        return HarmonicPath(tuple(base),0.0)
    def rank_positions(self):return [(1,3),(0,2),(2,1)]

def test_blind_selection_does_not_skip_unknown_reference():
    r=evaluate(FakeGraph(),['V',None,'I'])
    assert r['selected_position']==1
    assert r['selected_query_status']=='unanswerable'
    assert r['comparisons']['exact_chord']['targeted_gain']==0
    assert r['comparisons']['exact_chord']['random_gain']>0

def test_adjacent_requires_both_labels():
    x=metrics(['I','V','I'],['I',None,'I'])
    assert x['n_adjacent']==0
    assert x['exact_transition'] is None
    assert x['n_repeated_pairs']==1

def test_summary_song_level():
    x=evaluate(FakeGraph(),['V',None,'I'])
    s=summarize([{'status':'ok','result':x},{'status':'failed'}])
    assert s['n_evaluated']==1 and s['n_failed']==1
