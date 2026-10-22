from emh.harmony import generate_candidates

def test_minor_candidates_are_available():
    cs=generate_candidates("A","minor")
    assert [c.roman for c in cs[:7]] == ["i","ii°","III","iv","v","VI","VII"]
    assert len(cs)==10
