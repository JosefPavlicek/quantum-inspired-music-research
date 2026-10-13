from hooktheory.adapter import adapt
from hooktheory.loader import melody_only

def test_reference_firewall():
    rec={'annotations':{'num_beats':4,'meters':[{'beat':0,'beats_per_bar':4,'beat_unit':4}],
         'melody':[{'onset':0,'offset':1,'pitch_class':0}],
         'harmony':[{'onset':0,'offset':4,'root_pitch_class':0}]}}
    before=adapt(melody_only(rec))
    rec['annotations']['harmony'][0]['root_pitch_class']=7
    after=adapt(melody_only(rec))
    assert before==after

def test_compound_meter_not_silently_misinterpreted():
    rec={'num_beats':6,'meters':[{'beat':0,'beats_per_bar':6,'beat_unit':8}],
         'melody':[{'onset':0,'offset':1,'pitch_class':0}]}
    import pytest
    with pytest.raises(ValueError): adapt(rec)
