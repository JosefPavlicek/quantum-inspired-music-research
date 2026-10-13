"""Convert melody-only HookTheory annotations to frozen EMH input structures.

HookTheory 'beat' coordinates are used as quarter-note offsets for supported
simple meters. Compound-meter conversion must be validated before inclusion.
"""
from fractions import Fraction
from emh.model import NoteEvent
from emh.musicxml_loader import MelodyData


def frac(x): return Fraction(str(x)).limit_denominator(4096)

def adapt(melody):
    meters=melody["meters"]
    if len(meters)!=1 or meters[0]["beat"]!=0:
        raise ValueError("Requires one meter starting at beat 0")
    m=meters[0]; num=int(m["beats_per_bar"]); den=int(m["beat_unit"])
    if (num,den) not in {(2,4),(3,4),(4,4)}:
        raise ValueError("Compound meter pending verified time-base mapping")
    length=Fraction(num*4,den)
    total=frac(melody["num_beats"])
    notes=[]
    ordered=sorted(melody["melody"],key=lambda e:(e["onset"],e["offset"]))
    prev=Fraction(0)
    for e in ordered:
        onset=frac(e["onset"]); end=frac(e["offset"])
        if onset<prev or end<=onset or end>total:
            raise ValueError("Overlapping or out-of-range melody event")
        if onset>prev: notes.extend(_rest_events(prev,onset,length))
        pc=int(e["pitch_class"])%12
        notes.extend(_events(onset,end,length,pc))
        prev=end
    if prev<total: notes.extend(_rest_events(prev,total,length))
    if not notes: raise ValueError("Empty melody")
    nmeasures=int((total+length-1)//length)
    return MelodyData(notes=notes,time_signatures={i:f"{num}/{den}" for i in range(1,nmeasures+1)},key_signature_fifths=None,measure_count=nmeasures)

def _events(start,end,length,pc):
    from music21 import pitch
    result=[]
    while start<end:
        measure=int(start//length)+1
        boundary=length*measure
        stop=min(end,boundary)
        beat=start-length*(measure-1)+1
        name=pitch.Pitch(midi=60+pc).nameWithOctave if pc is not None else None
        result.append(NoteEvent(name,pc,start,stop-start,measure,beat,1.0 if beat==1 else 0.7,pc is None))
        start=stop
    return result

def _rest_events(start,end,length): return _events(start,end,length,None)
