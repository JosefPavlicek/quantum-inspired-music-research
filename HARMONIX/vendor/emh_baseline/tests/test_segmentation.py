from fractions import Fraction
from pathlib import Path
from emh.musicxml_loader import load_musicxml
from emh.segmentation import segment_notes
from emh.meter import metric_strength
F=Path(__file__).parent/"fixtures"

def test_4_4_two_half_measure_segments():
 m=load_musicxml(F/"test_4_4.musicxml"); s=segment_notes(m.notes,m.time_signatures)
 assert len(s)==2
 assert [x.start_beat for x in s]==[Fraction(1),Fraction(3)]
 assert [x.duration for x in s]==[Fraction(2),Fraction(2)]

def test_6_8_two_compound_pulses():
 m=load_musicxml(F/"test_6_8.musicxml"); s=segment_notes(m.notes,m.time_signatures)
 assert len(s)==2
 assert [x.start_beat for x in s]==[Fraction(1),Fraction(5,2)]
 assert [x.duration for x in s]==[Fraction(3,2),Fraction(3,2)]

def test_12_8_four_compound_pulses():
 m=load_musicxml(F/"test_12_8.musicxml"); s=segment_notes(m.notes,m.time_signatures)
 assert len(s)==4
 assert [x.duration for x in s]==[Fraction(3,2)]*4

def test_metric_weights_compound_meter():
 assert metric_strength("6/8",1)==1.5
 assert metric_strength("6/8",4)==1.2
 assert metric_strength("12/8",1)==1.5
 assert metric_strength("12/8",10)==1.2
