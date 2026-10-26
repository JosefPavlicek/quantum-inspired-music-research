from harmonix.corpus_audit import inspect_record, audit

def rec(split='TEST', meter=(4,4), artist='A', song='S'):
    return {'split':split,'artist':artist,'song':song,'annotations':{
        'num_beats':4,'meters':[{'beat':0,'beats_per_bar':meter[0],'beat_unit':meter[1]}],
        'melody':[{'onset':0,'offset':1,'pitch_class':0}],
        'harmony':[{'onset':0,'offset':4,'root_pitch_class':0}]}}

def test_preflight_rejects_compound_meter():
    assert inspect_record(rec(meter=(6,8))) == 'unsupported_meter'

def test_audit_counts_and_cross_split_duplicates():
    report, manifests = audit({'x':rec(),'y':rec(split='TRAIN'),'z':rec(meter=(6,8))})
    assert report['dataset_records']==3
    assert report['eligible_by_split']=={'TEST':1,'TRAIN':1}
    assert report['cross_split_artist_song_groups']==1
    assert len(manifests['TEST'])==1

def test_rank_deterministic():
    data={'a':rec(),'b':rec(song='other')}
    assert audit(data)[1]==audit(dict(reversed(list(data.items()))))[1]
