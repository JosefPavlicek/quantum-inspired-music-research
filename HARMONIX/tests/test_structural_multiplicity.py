import pytest
from harmonix.structural_multiplicity import analyze, CONTEXTS
from harmonix.rq_final_analysis import ARMS


def test_joint_intervals_cover_point_estimate_and_count_pairs():
    manifest = {'split': 'VALID', 'selected': [
        {'id': f'id{i}', 'artist': 'artist', 'song': f'song{i}'} for i in range(8)]}
    rows = []
    for i in range(8):
        strata = {}
        for context in CONTEXTS:
            strata[context] = {'n_pairs': 10, 'arms': {
                'corrected': {'generated_matches_reference_interval': 3},
                **{arm: {'generated_matches_reference_interval': 4+(i % 2)} for arm in ARMS}}}
        rows.append({'id': f'id{i}', 'status': 'ok',
                     'pair_diagnostics': {'transposition_strata': strata}})
    report = analyze(rows, manifest, repeats=120, seed=12)
    assert report['work_proxy_clusters'] == 8
    for context in CONTEXTS:
        for arm in ARMS:
            x = report['contrasts'][context][arm]
            assert x['n_pairs'] == 80
            assert x['simultaneous_ci95_pp'][0] <= x['effect_pp'] <= x['simultaneous_ci95_pp'][1]


def test_reject_train():
    with pytest.raises(ValueError):
        analyze([], {'split': 'TRAIN'}, repeats=100)
