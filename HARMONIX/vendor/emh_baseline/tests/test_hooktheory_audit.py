import json
from pathlib import Path
from experiments.audit_hooktheory_poc import audit

def test_audit_categories(tmp_path):
    summary=[{'id':'a','status':'ok'},{'id':'b','status':'excluded','reason':'meter'}]
    (tmp_path/'summary.json').write_text(json.dumps(summary))
    base={'status':'evaluated','reference_coverage_fraction':1.0,'dominant_reference_fraction':1.0,'mixed_reference':False,'root_agreement':False,'chord_agreement':False,'candidate_coverage':False,'root_candidate_coverage':True,'function_agreement':None,'generated_chord':'C','human_root_pc':2,'human_pitch_classes':[2,5,9]}
    rows=[dict(base,segment=0),dict(base,segment=1,candidate_coverage=True),dict(base,segment=2,candidate_coverage=True,chord_agreement=True,root_agreement=True)]
    (tmp_path/'a.json').write_text(json.dumps({'evaluation':{'segments':rows}}))
    result=audit(tmp_path)
    assert result['counts']['evaluated']==3
    assert result['counts']['reference_chord_unavailable']==1
    assert result['counts']['available_but_not_selected']==1
    assert result['counts']['exact_chord_match']==1
    assert (tmp_path/'diagnostics.md').exists()
