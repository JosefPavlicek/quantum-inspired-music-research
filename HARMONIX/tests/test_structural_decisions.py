from fractions import Fraction
from dataclasses import dataclass
from harmonix.structural_decisions import signature, structural_links
@dataclass
class Note:
    pitch_class:int
    duration:Fraction=Fraction(1)
    is_rest:bool=False
@dataclass
class Segment:
    notes:list
    duration:Fraction=Fraction(1)
def test_relative_melody_signature():
    assert signature(Segment([Note(0),Note(4)]))==signature(Segment([Note(2),Note(6)]))
def test_repetition_link():
    a=Segment([Note(0)]);b=Segment([Note(4),Note(7)]);c=Segment([Note(2)])
    assert structural_links([a,b,c])==[(0,2)]
def test_rest_no_links():
    r=Segment([Note(0,is_rest=True)])
    assert structural_links([r,r,r])==[]
