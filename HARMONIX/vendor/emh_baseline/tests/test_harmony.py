from emh.harmony import generate_candidates

def test_c_major_contains_seven_diatonic_triads():
 c=generate_candidates("C")
 assert [x.roman for x in c[:7]]==["I","ii","iii","IV","V","vi","vii°"]

def test_c_major_pitch_classes():
 c={x.roman:x for x in generate_candidates("C")}
 assert c["I"].pitch_classes==frozenset({0,4,7})
 assert c["V"].pitch_classes==frozenset({2,7,11})
 assert c["vii°"].pitch_classes==frozenset({2,5,11})

def test_function_labels_are_explicit():
 c={x.roman:x for x in generate_candidates("C")}
 assert c["I"].function=="tonic"
 assert c["ii"].function=="predominant"
 assert c["IV"].function=="predominant"
 assert c["V"].function=="dominant"

def test_common_sevenths_exist():
 romans={x.roman for x in generate_candidates("C")}
 assert {"ii7","V7","viiø7"} <= romans

def test_transposition_to_g_major():
 c={x.roman:x for x in generate_candidates("G")}
 assert c["I"].pitch_classes==frozenset({2,7,11})
 assert c["V"].pitch_classes==frozenset({2,6,9})
