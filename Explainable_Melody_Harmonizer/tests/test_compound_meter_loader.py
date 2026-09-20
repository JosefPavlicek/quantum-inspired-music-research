from fractions import Fraction
from pathlib import Path
from emh.musicxml_loader import load_musicxml
F=Path(__file__).parent/"fixtures"

def test_6_8_preserved():
 m=load_musicxml(F/"test_6_8.musicxml"); assert m.time_signatures[1]=="6/8"; assert sum((x.duration for x in m.notes),Fraction())==Fraction(3)
def test_6_8_rhythm_and_rest():
 m=load_musicxml(F/"test_6_8.musicxml"); assert [x.duration for x in m.notes]==[Fraction(3,2),Fraction(1,2),Fraction(1,4),Fraction(1,4),Fraction(1,2)]; assert sum(x.is_rest for x in m.notes)==1
def test_12_8_preserved():
 m=load_musicxml(F/"test_12_8.musicxml"); assert m.time_signatures[1]=="12/8"; assert sum((x.duration for x in m.notes),Fraction())==Fraction(6)
def test_12_8_rhythm_and_rest():
 m=load_musicxml(F/"test_12_8.musicxml"); assert [x.duration for x in m.notes]==[Fraction(3,2),Fraction(1,2),Fraction(1,2),Fraction(1,2),Fraction(1),Fraction(1,2),Fraction(1,4),Fraction(1,4),Fraction(1)]; assert sum(x.is_rest for x in m.notes)==1
