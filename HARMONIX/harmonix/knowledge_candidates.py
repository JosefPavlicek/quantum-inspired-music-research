"""Independent candidate vocabularies for controlled HARMONIX experiments.

This module does not import, monkeypatch or modify frozen EMH.
Reference annotations are never an input to candidate generation.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

Variant = Literal["baseline", "corrected", "extended"]

@dataclass(frozen=True)
class Candidate:
    symbol: str
    roman: str
    pitch_classes: frozenset[int]
    function: str

# Semitone distances of the diatonic degrees from the tonic.
SCALES = {"major": (0, 2, 4, 5, 7, 9, 11),
          "minor": (0, 2, 3, 5, 7, 8, 10)}
NAMES = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")
NAME_PC = {"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}
ROMANS = ("I", "II", "III", "IV", "V", "VI", "VII")
FUNCTIONS = ("tonic", "predominant", "tonic", "predominant", "dominant", "tonic", "dominant")
MAJOR_QUALITIES = ("maj", "min", "min", "maj", "maj", "min", "dim")
MINOR_QUALITIES = ("min", "dim", "maj", "min", "min", "maj", "maj")
TRIADS = {"maj": (0,4,7), "min": (0,3,7), "dim": (0,3,6)}
SEVENTHS = {"maj7":(0,4,7,11), "min7":(0,3,7,10),
            "dom7":(0,4,7,10), "halfdim7":(0,3,6,10)}

def tonic_pc(name: str) -> int:
    if not name or name[0].upper() not in NAME_PC:
        raise ValueError(f"Invalid tonic: {name!r}")
    base=NAME_PC[name[0].upper()]
    suffix=name[1:].replace("-", "b")
    if any(ch not in "#b" for ch in suffix):
        raise ValueError(f"Invalid tonic: {name!r}")
    return (base + suffix.count("#") - suffix.count("b")) % 12

def _candidate(root: int, intervals: tuple[int,...], roman: str, function: str, suffix: str) -> Candidate:
    return Candidate(NAMES[root]+suffix, roman,
                     frozenset((root+i)%12 for i in intervals), function)

def _triad(root:int, quality:str, degree:int) -> Candidate:
    roman=ROMANS[degree] if quality=="maj" else ROMANS[degree].lower()
    if quality=="dim": roman+="°"
    return _candidate(root,TRIADS[quality],roman,FUNCTIONS[degree],
                      {"maj":"","min":"m","dim":"dim"}[quality])

def _seventh(root:int, quality:str, degree:int) -> Candidate:
    roman=ROMANS[degree]
    if quality in {"min7","halfdim7"}:roman=roman.lower()
    roman += {"maj7":"maj7","min7":"7","dom7":"7","halfdim7":"ø7"}[quality]
    return _candidate(root,SEVENTHS[quality],roman,FUNCTIONS[degree],
                      {"maj7":"maj7","min7":"m7","dom7":"7","halfdim7":"m7b5"}[quality])

def generate(tonic: str, mode: str, variant: Variant = "corrected") -> list[Candidate]:
    """Build a reference-blind candidate vocabulary. For baseline use frozen EMH directly.

    Corrected: 7 diatonic triads plus ii7, V7, vii7; in minor, V/V7
    use harmonic minor's raised leading tone and iiø7 is included.
    Extended: corrected + diatonic sevenths on remaining degrees and
    secondary dominants V7/ii, V7/iii, V7/IV, V7/V, V7/vi (major),
    V7/III, V7/iv, V7/v, V7/VI, V7/VII (minor).
    """
    if variant == "baseline":
        raise ValueError("For baseline call the frozen EMH generator unchanged; do not approximate it here")
    if variant not in ("corrected", "extended"):
        raise ValueError(f"Unknown variant: {variant}")
    if mode not in SCALES:
        raise ValueError(f"Unsupported mode: {mode}")
    pc=tonic_pc(tonic)
    roots=[(pc+d)%12 for d in SCALES[mode]]
    qualities=list(MAJOR_QUALITIES if mode=="major" else MINOR_QUALITIES)
    if mode=="minor": qualities[4]="maj" # raised leading tone in dominant
    out=[_triad(root, quality, degree) for degree,(root,quality) in enumerate(zip(roots,qualities))]
    if mode=="major":
        seventh_qualities={1:"min7",4:"dom7",6:"halfdim7"}
    else:
        seventh_qualities={1:"halfdim7",4:"dom7",6:"dom7"}
    for degree,quality in seventh_qualities.items():
        out.append(_seventh(roots[degree],quality,degree))
    if variant=="extended":
        if mode=="major":
            extra={0:"maj7",2:"min7",3:"maj7",5:"min7"}
            targets=(1,2,3,4,5)
        else:
            # Natural-minor diatonic 7ths except altered dominant already corrected.
            extra={0:"min7",2:"maj7",3:"min7",5:"maj7"}
            targets=(2,3,4,5,6)
        for degree,quality in extra.items():
            out.append(_seventh(roots[degree],quality,degree))
        for degree in targets:
            target_root=roots[degree]
            secondary_root=(target_root+7)%12
            c=_candidate(secondary_root,SEVENTHS["dom7"],
                         "V7/"+ROMANS[degree],"dominant","7")
            out.append(c)
    # Same pitch-class set may be present with different function/roman label.
    # Preserve distinct analytical labels; exact-coverage metrics use pitch classes.
    return out
