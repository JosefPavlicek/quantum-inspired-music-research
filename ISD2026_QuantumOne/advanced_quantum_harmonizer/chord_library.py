# chord_library.py

from dataclasses import dataclass
from typing import Dict, List, Tuple, Set


ALIASES = {
    "H": "B",
    "C#": "Db",
    "D#": "Eb",
    "F#": "Gb",
    "G#": "Ab",
    "A#": "Bb",
}


PC_TO_SEMITONE = {
    "C": 0,
    "Db": 1,
    "D": 2,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "Gb": 6,
    "G": 7,
    "Ab": 8,
    "A": 9,
    "Bb": 10,
    "B": 11,
}

SEMITONE_TO_PC = {v: k for k, v in PC_TO_SEMITONE.items()}


@dataclass(frozen=True)
class ChordDef:
    name: str
    root: str
    tones: Tuple[str, ...]
    function: str          # T / S / D
    quality: str           # major / minor / dim / dom7 / maj7 / min7 / halfdim7
    chord_type: str        # triad / seventh

    @property
    def tone_set(self) -> Set[str]:
        return set(self.tones)

    @property
    def third(self) -> str | None:
        return self.tones[1] if len(self.tones) >= 2 else None

    @property
    def fifth(self) -> str | None:
        return self.tones[2] if len(self.tones) >= 3 else None

    @property
    def seventh(self) -> str | None:
        return self.tones[3] if len(self.tones) >= 4 else None


def normalize_pc(pc: str) -> str:
    pc = pc.strip()
    if len(pc) >= 2 and pc[1] in ("b", "#"):
        name = pc[0].upper() + pc[1]
    else:
        name = pc[0].upper() + pc[1:]
    name = ALIASES.get(name, name)
    if name not in PC_TO_SEMITONE:
        raise ValueError(f"Unknown pitch class: {pc}")
    return name


def semitone_to_pc(semitone: int) -> str:
    return SEMITONE_TO_PC[semitone % 12]


def midi_to_pc(midi: int) -> str:
    return semitone_to_pc(midi % 12)


def transpose_pc(pc: str, semitone_shift: int) -> str:
    base = PC_TO_SEMITONE[normalize_pc(pc)]
    return semitone_to_pc(base + semitone_shift)


def make_triad(name: str, root: str, third: str, fifth: str, function: str, quality: str) -> ChordDef:
    return ChordDef(
        name=name,
        root=root,
        tones=(root, third, fifth),
        function=function,
        quality=quality,
        chord_type="triad",
    )


def make_seventh(name: str, root: str, third: str, fifth: str, seventh: str, function: str, quality: str) -> ChordDef:
    return ChordDef(
        name=name,
        root=root,
        tones=(root, third, fifth, seventh),
        function=function,
        quality=quality,
        chord_type="seventh",
    )


DIATONIC_TRIADS: Dict[str, ChordDef] = {
    "C":    make_triad("C",    "C", "E",  "G",  "T", "major"),
    "Dm":   make_triad("Dm",   "D", "F",  "A",  "S", "minor"),
    "Em":   make_triad("Em",   "E", "G",  "B",  "T", "minor"),
    "F":    make_triad("F",    "F", "A",  "C",  "S", "major"),
    "G":    make_triad("G",    "G", "B",  "D",  "D", "major"),
    "Am":   make_triad("Am",   "A", "C",  "E",  "T", "minor"),
    "Bdim": make_triad("Bdim", "B", "D",  "F",  "D", "dim"),
}

DIATONIC_SEVENTHS: Dict[str, ChordDef] = {
    "Cmaj7":  make_seventh("Cmaj7",  "C", "E",  "G",  "B",  "T", "maj7"),
    "Dm7":    make_seventh("Dm7",    "D", "F",  "A",  "C",  "S", "min7"),
    "Em7":    make_seventh("Em7",    "E", "G",  "B",  "D",  "T", "min7"),
    "Fmaj7":  make_seventh("Fmaj7",  "F", "A",  "C",  "E",  "S", "maj7"),
    "G7":     make_seventh("G7",     "G", "B",  "D",  "F",  "D", "dom7"),
    "Am7":    make_seventh("Am7",    "A", "C",  "E",  "G",  "T", "min7"),
    "Bm7b5":  make_seventh("Bm7b5",  "B", "D",  "F",  "A",  "D", "halfdim7"),
}

SECONDARY_DOMINANTS: Dict[str, ChordDef] = {
    "A7": make_seventh("A7", "A", "Db", "E",  "G",  "D", "dom7"),
    "B7": make_seventh("B7", "B", "Eb", "Gb", "A",  "D", "dom7"),
    "C7": make_seventh("C7", "C", "E",  "G",  "Bb", "D", "dom7"),
    "D7": make_seventh("D7", "D", "Gb", "A",  "C",  "D", "dom7"),
    "E7": make_seventh("E7", "E", "Ab", "B",  "D",  "D", "dom7"),
}

DOM_TARGETS = {
    "A7": "Dm",
    "B7": "Em",
    "C7": "F",
    "D7": "G",
    "E7": "Am",
}


def build_chord_pool(
    allow_triads: bool = True,
    allow_sevenths: bool = True,
    allow_secondary_dominants: bool = False,
) -> Dict[str, ChordDef]:
    pool: Dict[str, ChordDef] = {}

    if allow_triads:
        pool.update(DIATONIC_TRIADS)

    if allow_sevenths:
        pool.update(DIATONIC_SEVENTHS)

    if allow_secondary_dominants:
        pool.update(SECONDARY_DOMINANTS)

    return pool


def chord_names_by_function(
    chord_pool: Dict[str, ChordDef],
    function: str,
) -> List[str]:
    return [name for name, chord in chord_pool.items() if chord.function == function]


def chords_containing_pitch_classes(
    chord_pool: Dict[str, ChordDef],
    pitch_classes: List[str],
) -> List[str]:
    pcs = set(pitch_classes)
    out = []
    for name, chord in chord_pool.items():
        if pcs.issubset(chord.tone_set):
            out.append(name)
    return out


def chords_matching_any_pitch_class(
    chord_pool: Dict[str, ChordDef],
    pitch_classes: List[str],
) -> List[str]:
    pcs = set(pitch_classes)
    out = []
    for name, chord in chord_pool.items():
        if chord.tone_set.intersection(pcs):
            out.append(name)
    return out