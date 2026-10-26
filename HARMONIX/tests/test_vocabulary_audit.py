from harmonix.vocabulary_audit import classify, audit_record, summarize

def test_quality():
    assert classify(0,[4,3])[0]=='major_triad'
    assert classify(0,[4,3,3])[0]=='dominant_seventh'
    assert classify(0,[4,3,2])[0]=='major_sixth'
    assert classify(0,[2,5])[0]=='sus2'
    assert classify(0,[4,3,3,4])[0]=='extended_or_complex'

def test_diagnosis():
    rows=audit_record({'audit_rows':[{'status':'out_of_vocabulary','quality':'major_triad','root_match_any':True,'pitch_class_match_any':False},
                                     {'status':'mixed_or_partial','quality':None}]})
    assert rows[0]['diagnosis']=='root_present_but_pitch_classes_differ'
    assert summarize(rows,[])['n_segments']==2
