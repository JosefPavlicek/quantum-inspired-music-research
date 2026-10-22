"""Independent, immutable harmonic knowledge objects (no EMH imports).

Pitch classes use C=0, C#/Db=1 ... B/H=11. Octaves and voicings are separate.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class Quality(str, Enum):
    MAJOR = 'major'
    MINOR = 'minor'
    DIMINISHED = 'diminished'
    AUGMENTED = 'augmented'
    SUS2 = 'sus2'
    SUS4 = 'sus4'


TRIAD = {
    Quality.MAJOR: (0, 4, 7), Quality.MINOR: (0, 3, 7),
    Quality.DIMINISHED: (0, 3, 6), Quality.AUGMENTED: (0, 4, 8),
    Quality.SUS2: (0, 2, 7), Quality.SUS4: (0, 5, 7),
}


@dataclass(frozen=True)
class Chord:
    root_pc: int
    quality: Quality
    # Intervals above root in semitones, including sevenths, ninths, etc.
    extensions: tuple[int, ...] = ()
    # Explicit modifications (e.g. b5 is interval 6), represented as intervals
    # to remove and add; avoids conflating an altered tone with a new extension.
    omit_intervals: tuple[int, ...] = ()
    add_intervals: tuple[int, ...] = ()
    bass_pc: int | None = None
    # Optional analytical annotation; not part of chord identity.
    function: str | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.root_pc <= 11:
            raise ValueError('root_pc must be in 0..11')
        if self.bass_pc is not None and not 0 <= self.bass_pc <= 11:
            raise ValueError('bass_pc must be in 0..11')
        if any(not 0 <= n <= 24 for n in (*self.extensions, *self.omit_intervals, *self.add_intervals)):
            raise ValueError('intervals must be in 0..24 semitones')
        if 0 in self.omit_intervals:
            raise ValueError('Root omission is not supported by this initial model')
        if self.function is not None and not self.function.strip():
            raise ValueError('function annotation cannot be blank')

    @property
    def intervals(self) -> tuple[int, ...]:
        values = (set(TRIAD[self.quality]) | set(self.extensions) | set(self.add_intervals)) - set(self.omit_intervals)
        return tuple(sorted(values))

    @property
    def pitch_classes(self) -> frozenset[int]:
        return frozenset((self.root_pc + i) % 12 for i in self.intervals)

    @property
    def effective_bass_pc(self) -> int:
        return self.root_pc if self.bass_pc is None else self.bass_pc

    @property
    def inversion(self) -> int | None:
        """0=root, 1=third, 2=fifth, 3=seventh; None=non-chord bass/ambiguous.

        Extended chord inversions beyond seventh are intentionally not classified.
        """
        target = (self.effective_bass_pc - self.root_pc) % 12
        structural = [i for i in self.intervals if i < 12]
        if target not in structural:
            return None
        # The bass may be an added 6th, not a classical inversion.
        triad = [i for i in TRIAD[self.quality] if i in self.intervals]
        seventh = [i for i in (9, 10, 11) if i in self.extensions and i in self.intervals and i not in triad]
        tones = triad + seventh
        return tones.index(target) if target in tones else None

    def harmonic_identity(self) -> tuple:
        """Identity without bass, voicing or functional annotation."""
        return self.root_pc, self.quality.value, self.intervals

    def realization_identity(self) -> tuple:
        """Chord identity plus bass, still independent of voicing."""
        return self.harmonic_identity(), self.effective_bass_pc


@dataclass(frozen=True)
class Voicing:
    """Absolute MIDI pitches; independent of chord identity and inversion."""
    midi_notes: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.midi_notes or any(not 0 <= n <= 127 for n in self.midi_notes):
            raise ValueError('Voicing requires valid MIDI notes (0..127)')

    def matches(self, chord: Chord) -> bool:
        return (frozenset(n % 12 for n in self.midi_notes) <= chord.pitch_classes
                and min(self.midi_notes) % 12 == chord.effective_bass_pc)


def classify_change(before: Chord, after: Chord) -> str:
    """Structural comparison; does NOT infer whether human intent was preserved."""
    if before.realization_identity() == after.realization_identity():
        return 'same_harmony_and_bass'
    if before.harmonic_identity() == after.harmonic_identity():
        return 'bass_or_inversion_change'
    if before.root_pc == after.root_pc:
        return 'chord_quality_or_extension_change'
    return 'root_or_harmony_change'
