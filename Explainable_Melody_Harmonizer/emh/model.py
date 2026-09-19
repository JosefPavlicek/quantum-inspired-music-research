"""Internal domain model.

These structures deliberately isolate the harmonization algorithm from
music21-specific objects.
"""

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Optional


@dataclass(frozen=True)
class NoteEvent:
    pitch: Optional[str]
    pitch_class: Optional[int]
    onset: Fraction
    duration: Fraction
    measure: int
    beat: Fraction
    metric_strength: float
    is_rest: bool = False


@dataclass
class HarmonicSegment:
    index: int
    measure: int
    start_beat: Fraction
    duration: Fraction
    notes: list[NoteEvent] = field(default_factory=list)


@dataclass(frozen=True)
class ChordCandidate:
    symbol: str
    roman: str
    pitch_classes: frozenset[int]
    function: str


@dataclass
class ScoreComponents:
    melody_compatibility: float = 0.0
    functional_transition: float = 0.0
    persistence: float = 0.0
    cadence: float = 0.0
    local_score: float = 0.0
    path_score: float = 0.0


@dataclass
class Decision:
    segment: HarmonicSegment
    selected: ChordCandidate
    scores: ScoreComponents
    alternatives: list = field(default_factory=list)
