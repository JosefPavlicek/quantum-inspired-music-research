import pytest
from harmonix.structural_error_analysis import analyze, group_key


def _row(ident, delta):
    scores = {'corrected': {'chord_agreement': 0.2},
              'repetition': {'chord_agreement': 0.2 + delta},
              'function': {'chord_agreement': 0.2},
              'combined': {'chord_agreement': 0.2 + delta}}
    return {'id': ident, 'status': 'ok', 'scores': scores}


def test_group_key():
    assert group_key({'id': 'a', 'artist': ' Artist ', 'song': ' SONG'}) == group_key({'id': 'b', 'artist': 'artist', 'song': 'song'})
    assert group_key({'id': 'a', 'artist': '', 'song': 'song'}) != group_key({'id': 'b', 'artist': '', 'song': 'song'})


def test_paired_analysis_and_cluster_count():
    manifest = {'split': 'TRAIN', 'selected': [{'id': 'a', 'artist': 'A', 'song': 'S'}, {'id': 'b', 'artist': 'A', 'song': 'S'}, {'id': 'c', 'artist': 'B', 'song': 'T'}]}
    report = analyze([_row('a', 0.1), _row('b', 0.1), _row('c', -0.1)], manifest, bootstrap=100, seed=1)
    assert report['n_song_proxy_clusters'] == 2
    metric = report['metrics']['chord_agreement']['repetition']
    assert metric['mean_difference_percentage_points'] == pytest.approx(100 / 30)
    assert metric['record_outcomes'] == {'improved': 2, 'worsened': 1}


def test_duplicate_id_rejected():
    manifest = {'split': 'TRAIN', 'selected': [{'id': 'a'}]}
    with pytest.raises(ValueError, match='duplicate ID'):
        analyze([_row('a', 0), _row('a', 0)], manifest, bootstrap=100)


def test_test_split_rejected():
    with pytest.raises(ValueError, match='TRAIN'):
        analyze([], {'split': 'TEST', 'selected': []}, bootstrap=100)
