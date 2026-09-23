"""Transparent melody-only key detection for EMH.

Uses duration-weighted pitch-class histograms correlated with the classic
Krumhansl-Kessler major/minor key profiles. Harmony annotations are never read.
"""
from dataclasses import dataclass
from math import sqrt
from emh.model import NoteEvent

# Krumhansl-Kessler tonal hierarchy profiles, C major / C minor orientation.
_MAJOR = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
_MINOR = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)
_NAMES_SHARP = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

@dataclass(frozen=True)
class KeyScore:
    tonic: str
    mode: str
    score: float

    @property
    def name(self) -> str:
        return f"{self.tonic} {self.mode}"

@dataclass(frozen=True)
class KeyDetectionResult:
    tonic: str
    mode: str
    score: float
    ranking: tuple[KeyScore, ...]

    @property
    def name(self) -> str:
        return f"{self.tonic} {self.mode}"

def _weighted_histogram(notes: list[NoteEvent]) -> list[float]:
    hist = [0.0] * 12
    for n in notes:
        if n.is_rest or n.pitch_class is None:
            continue
        # Duration is the only weighting used here: transparent and independent
        # of the later harmony-scoring metric weights.
        hist[n.pitch_class] += float(n.duration)
    if sum(hist) == 0:
        raise ValueError("Key detection requires at least one sounding note.")
    return hist

def _pearson(a, b) -> float:
    ma, mb = sum(a)/len(a), sum(b)/len(b)
    da = [x-ma for x in a]; db = [x-mb for x in b]
    den = sqrt(sum(x*x for x in da) * sum(x*x for x in db))
    return 0.0 if den == 0 else sum(x*y for x, y in zip(da, db)) / den

def _rotated_profile(profile, tonic_pc: int):
    # profile[i] describes pitch class i relative to tonic C.
    return tuple(profile[(pc-tonic_pc) % 12] for pc in range(12))

def detect_key(notes: list[NoteEvent]) -> KeyDetectionResult:
    """Rank all 24 major/minor keys from melody alone."""
    hist = _weighted_histogram(notes)
    scores = []
    for pc, tonic in enumerate(_NAMES_SHARP):
        scores.append(KeyScore(tonic, "major", _pearson(hist, _rotated_profile(_MAJOR, pc))))
        scores.append(KeyScore(tonic, "minor", _pearson(hist, _rotated_profile(_MINOR, pc))))
    # Deterministic ties: major before minor, then pitch class order above.
    order = {name: i for i, name in enumerate(_NAMES_SHARP)}
    scores.sort(key=lambda x: (-x.score, 0 if x.mode == "major" else 1, order[x.tonic]))
    best = scores[0]
    return KeyDetectionResult(best.tonic, best.mode, best.score, tuple(scores))
