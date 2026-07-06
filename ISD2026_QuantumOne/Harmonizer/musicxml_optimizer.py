# musicxml_optimizer.py
# Post-processor for harmonizer output MusicXML.
#
# Spustit:
#   python3 musicxml_optimizer.py
# nebo jako modul:
#   python3 -m Harmonizer.musicxml_optimizer
#
# Co to umí (v bodech):
# 1) Zachová melodii (P1) beze změn.
# 2) Vygeneruje NOVÝ MusicXML (fresh export):
#    - P1: původní melodie + NOVÁ <harmony> (původní harmony ignoruje)
#    - P2: NOVÁ basová / LH akordová linka v basovém klíči
# 3) „Humanize“: sníží zbytečné změny akordů uvnitř taktu.
# 4) Respektuje harmonizer:
#    - původní akordy jsou vždy kandidáti s preferencí
#    - nahrazuje je až když jsou „nelidské“ (špatně sedí na melodii / funkci / rytmus změn)
# 5) Kvantově-logický výběr subdominanty a dominanty:
#    - hledá napětí (S) a vyvrcholení (D) jen pokud to dává smysl (nenutí 4/5 vždy)
#    - používá amplitudové skórování + DP (interferenční volba nejlepší cesty)
# 6) Umí přidat:
#    - sekundární dominanty (V/x)
#    - mimotónální dominanty (sekundární)
#    - tritonové substituce (bII7 místo V7)
#    - obraty / slash bass (už bylo, ponecháno)
# 7) Umí upravit barvu akordu:
#    - zmenšit: 7 → triáda (kvintakord)
#    - rozšířit: 6 / 9 / 11 / 13 (střídmě a kytarově)
# 8) Rytmická „slušnost“:
#    - penalizuje změny akordů na melodických útocích
#    - zvlášť na 2. a 4. době (pokud to není nutné)
# 9) Notová validita (Sibelius/Soundslice):
#    - P2 používá správné type + dot pro délky (včetně dotted-half)
#    - všechny tóny akordu v jedné voice
# 10) Kadence a sustain:
#     - volitelná kadence (C nebo G7 na konci)
#     - pokud je na konci jen jeden akord, nechá ho znít do konce posledního taktu
# 11) Preferuje polohově a basově blízké pokračování:
#     - sousední akordy drží podobnou basovou polohu a podobný registr
#     - omezuje skákání tam a zpět mezi hlubokou a střední polohou
#     - větší skok dovolí spíše u mimotónálních dominant, substitucí a kadencí
#     - stále ctí návrhy harmonizeru; mění je spíš jemně (obrat, bas, barva)
#
# Poznámky k MusicXML:
# - kind@text nikdy nesmí obsahovat root (jinak GG7 apod.)
# - když v P1 neexistuje nota začínající přesně v čase změny akordu, použije se <offset> (divisions)

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
import xml.etree.ElementTree as ET
import random
from pathlib import Path
import argparse
import copy

# ----------------------------
# Pitch helpers (flat-preferred)
# ----------------------------
PC_TO_SEMITONE = {
    "C": 0, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5,
    "Gb": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11
}
SEMITONE_TO_PC = {v: k for k, v in PC_TO_SEMITONE.items()}

STEP_ALTER_TO_PC: Dict[Tuple[str, int], str] = {
    ("C", 0): "C",
    ("D", -1): "Db",
    ("D", 0): "D",
    ("E", -1): "Eb",
    ("E", 0): "E",
    ("F", 0): "F",
    ("G", -1): "Gb",
    ("G", 0): "G",
    ("A", -1): "Ab",
    ("A", 0): "A",
    ("B", -1): "Bb",
    ("B", 0): "B",
}

PC_TO_STEP_ALTER: Dict[str, Tuple[str, int]] = {
    "C": ("C", 0),
    "Db": ("D", -1),
    "D": ("D", 0),
    "Eb": ("E", -1),
    "E": ("E", 0),
    "F": ("F", 0),
    "Gb": ("G", -1),
    "G": ("G", 0),
    "Ab": ("A", -1),
    "A": ("A", 0),
    "Bb": ("B", -1),
    "B": ("B", 0),
}

MAJOR_SCALE_ST = [0, 2, 4, 5, 7, 9, 11]

def midi_to_step_alter_oct(midi: int) -> Tuple[str, int, int]:
    pc = SEMITONE_TO_PC[midi % 12]
    step, alter = PC_TO_STEP_ALTER[pc]
    octave = (midi // 12) - 1  # scientific pitch (C4=60)
    return step, alter, octave

def pc_oct_to_midi(pc: str, octave: int) -> int:
    return 12 * (octave + 1) + PC_TO_SEMITONE[pc]

def parse_pitch_to_pc(note_el: ET.Element) -> Optional[str]:
    """Return pitch-class from <note>, None if rest."""
    if note_el.find("rest") is not None:
        return None
    pitch = note_el.find("pitch")
    if pitch is None:
        return None
    step = pitch.findtext("step")
    alter = int(pitch.findtext("alter") or "0")
    return STEP_ALTER_TO_PC.get((step, alter), None)

# ----------------------------
# Chord symbol parsing / building
# ----------------------------
@dataclass(frozen=True)
class ChordSpec:
    root_pc: str
    quality: str  # "maj", "min", "dom", "hdim"
    has7: bool
    ext: Optional[str] = None  # "sus4","add9","6","9","11","13"
    slash_bass_pc: Optional[str] = None  # inversion bass

def parse_chord_text(text: str) -> ChordSpec:
    """
    Supports: Cmaj7, Dm7, G7, Bm7b5, A7, C6, C9, C13, Csus4...
    Flats preferred (Bb, Db...)
    """
    t = (text or "").strip()
    if not t:
        return ChordSpec("C", "maj", True, None, None)

    slash_bass = None
    if "/" in t:
        t, bass = t.split("/", 1)
        slash_bass = bass.strip() if bass else None

    root = t[0].upper()
    rest = t[1:]
    if rest.startswith("b"):
        root += "b"
        rest = rest[1:]
    root_pc = root

    # extensions parsing (simple)
    ext = None
    if "sus4" in t:
        ext = "sus4"
    elif "add9" in t:
        ext = "add9"
    elif t.endswith("13"):
        ext = "13"
    elif t.endswith("11"):
        ext = "11"
    elif t.endswith("9"):
        ext = "9"
    elif t.endswith("6"):
        ext = "6"

    if "m7b5" in t:
        return ChordSpec(root_pc, "hdim", True, None, slash_bass)
    if "maj7" in t:
        return ChordSpec(root_pc, "maj", True, ext, slash_bass)
    if "m7" in t:
        return ChordSpec(root_pc, "min", True, ext, slash_bass)
    if t.endswith("7"):
        return ChordSpec(root_pc, "dom", True, ext, slash_bass)

    # minor triad
    if "m" in t[1:2]:
        return ChordSpec(root_pc, "min", False, ext, slash_bass)

    return ChordSpec(root_pc, "maj", False, ext, slash_bass)

def chord_text_for_display(ch: ChordSpec) -> str:
    base = ch.root_pc
    if ch.quality == "maj" and ch.has7:
        base += "maj7"
    elif ch.quality == "min" and ch.has7:
        base += "m7"
    elif ch.quality == "dom" and ch.has7:
        base += "7"
    elif ch.quality == "hdim" and ch.has7:
        base += "m7b5"
    else:
        if ch.quality == "min":
            base += "m"

    if ch.ext:
        base += ch.ext if ch.ext in ("6","9","11","13") else ch.ext
    return base

def kind_text_suffix(ch: ChordSpec) -> str:
    # MUST be without root
    if ch.quality == "maj" and ch.has7:
        suf = "maj7"
    elif ch.quality == "min" and ch.has7:
        suf = "m7"
    elif ch.quality == "dom" and ch.has7:
        suf = "7"
    elif ch.quality == "hdim" and ch.has7:
        suf = "m7b5"
    else:
        suf = "m" if ch.quality == "min" else ""

    if ch.ext:
        suf += ch.ext
    return suf

def chord_tones_pcs(ch: ChordSpec) -> List[str]:
    r = PC_TO_SEMITONE[ch.root_pc]
    if ch.quality == "maj":
        triad = [0, 4, 7]
        seventh = 11
    elif ch.quality == "min":
        triad = [0, 3, 7]
        seventh = 10
    elif ch.quality == "dom":
        triad = [0, 4, 7]
        seventh = 10
    else:  # hdim
        triad = [0, 3, 6]
        seventh = 10

    pcs = [SEMITONE_TO_PC[(r + iv) % 12] for iv in triad]
    if ch.has7:
        pcs.append(SEMITONE_TO_PC[(r + seventh) % 12])

    # extensions
    if ch.ext == "sus4":
        sus_pc = SEMITONE_TO_PC[(r + 5) % 12]
        if len(pcs) >= 2:
            pcs[1] = sus_pc
    elif ch.ext == "6":
        pcs.append(SEMITONE_TO_PC[(r + 9) % 12])
    elif ch.ext in ("9", "add9"):
        pcs.append(SEMITONE_TO_PC[(r + 14) % 12])
    elif ch.ext == "11":
        pcs.append(SEMITONE_TO_PC[(r + 17) % 12])
    elif ch.ext == "13":
        pcs.append(SEMITONE_TO_PC[(r + 21) % 12])

    out: List[str] = []
    for p in pcs:
        if p not in out:
            out.append(p)
    return out

def make_guitar_friendly(ch: ChordSpec) -> ChordSpec:
    """
    Kytarový filtr – konzervativní, ale splňuje zadání:
    - maj7 + (9/11/13/add9) často nevychází -> shodit ext
    - hdim + ext nechceme
    - slash + ext shodíme (příliš chaos)
    - dom: povolíme 9/13/sus4/6 (ale bez 11)
    - min: povolíme 6/9/11 (ale bez 13)
    """
    if ch.slash_bass_pc and ch.ext:
        return ChordSpec(ch.root_pc, ch.quality, ch.has7, None, ch.slash_bass_pc)

    if ch.quality == "maj" and ch.has7 and ch.ext in ("add9","9","11","13"):
        return ChordSpec(ch.root_pc, ch.quality, True, None, ch.slash_bass_pc)

    if ch.quality == "hdim" and ch.ext:
        return ChordSpec(ch.root_pc, ch.quality, ch.has7, None, ch.slash_bass_pc)

    if ch.quality == "dom":
        if ch.ext == "11":
            return ChordSpec(ch.root_pc, ch.quality, ch.has7, None, ch.slash_bass_pc)
        # ok: 9/13/6/sus4
        return ch

    if ch.quality == "min":
        if ch.ext == "13":
            return ChordSpec(ch.root_pc, ch.quality, ch.has7, None, ch.slash_bass_pc)
        return ch

    # maj triad ok: 6/9 (bez maj7)
    if ch.quality == "maj" and (not ch.has7) and ch.ext in ("11","13"):
        return ChordSpec(ch.root_pc, ch.quality, False, None, ch.slash_bass_pc)

    return ch

def choose_voicing_midis_bass_safe(
    pcs: List[str],
    base_octave: int = 3,
    force_bass_pc: Optional[str] = None,
    min_bass_midi: int = 43,   # ~G2
    max_top_midi: int = 64,    # ~E4
) -> List[int]:
    pcs2 = pcs[:]
    if force_bass_pc and force_bass_pc in pcs2:
        pcs2.remove(force_bass_pc)
        pcs2 = [force_bass_pc] + pcs2

    bass = pc_oct_to_midi(pcs2[0], base_octave)
    while bass < min_bass_midi:
        bass += 12

    midis = [bass]
    prev = bass
    for pc in pcs2[1:]:
        m = pc_oct_to_midi(pc, base_octave)
        while m <= prev:
            m += 12
        midis.append(m)
        prev = m

    # limit 4 notes max
    while len(midis) < 4:
        midis.append(midis[-1] + 12)

    while max(midis[:4]) > max_top_midi:
        midis = [m - 12 for m in midis]

    while min(midis[:4]) < min_bass_midi - 12:
        midis = [m + 12 for m in midis]

    return midis[:4]

# ----------------------------
# Tonal / functional helpers (rule-based = "quantum logical")
# ----------------------------
def infer_key_from_key_signature(measure0: ET.Element) -> Optional[str]:
    """
    Zkusí přečíst <fifths>. Pro jednoduchost mapujeme jen běžné durové tóniny.
    Pokud to nejde, vrátí None a použijeme melodii.
    """
    fifths_txt = measure0.findtext("./attributes/key/fifths")
    if fifths_txt is None:
        return None
    try:
        fifths = int(fifths_txt)
    except:
        return None

    # circle of fifths major (flats as needed)
    mapping = {
        -7: "Cb", -6: "Gb", -5: "Db", -4: "Ab", -3: "Eb", -2: "Bb", -1: "F",
         0: "C",
         1: "G", 2: "D", 3: "A", 4: "E", 5: "B", 6: "Gb", 7: "Db"
    }
    return mapping.get(fifths, None)

def infer_key_from_melody(bars_mel: List[List[Optional[str]]]) -> str:
    notes: List[str] = []
    for bar in bars_mel:
        for pc in bar:
            if pc is not None:
                notes.append(pc)
    if not notes:
        return "C"

    best_key = "C"
    best_score = -1
    for key_pc in PC_TO_SEMITONE.keys():
        root_st = PC_TO_SEMITONE[key_pc]
        scale = {(root_st + x) % 12 for x in MAJOR_SCALE_ST}
        sc = 0
        for n in notes:
            sc += 1 if PC_TO_SEMITONE[n] in scale else 0
        if sc > best_score:
            best_score = sc
            best_key = key_pc
    return best_key

def diatonic_chords_in_key(key_pc: str) -> Dict[str, ChordSpec]:
    """
    Durová diatonika (základ):
      I maj7, ii m7, iii m7, IV maj7, V7, vi m7, viiø m7b5
    """
    root = PC_TO_SEMITONE[key_pc]
    deg = [(root + x) % 12 for x in MAJOR_SCALE_ST]
    pcs = [SEMITONE_TO_PC[x] for x in deg]
    return {
        "I":   ChordSpec(pcs[0], "maj", True),
        "ii":  ChordSpec(pcs[1], "min", True),
        "iii": ChordSpec(pcs[2], "min", True),
        "IV":  ChordSpec(pcs[3], "maj", True),
        "V":   ChordSpec(pcs[4], "dom", True),
        "vi":  ChordSpec(pcs[5], "min", True),
        "vii": ChordSpec(pcs[6], "hdim", True),
    }

def chord_function_TSD(ch: ChordSpec, key_pc: str) -> str:
    d = diatonic_chords_in_key(key_pc)
    def base_sig(c: ChordSpec) -> Tuple[str, str, bool]:
        return (c.root_pc, c.quality, c.has7)
    sig = base_sig(ChordSpec(ch.root_pc, ch.quality, ch.has7))
    if sig in (base_sig(d["I"]), base_sig(d["vi"]), base_sig(d["iii"])):
        return "T"
    if sig in (base_sig(d["ii"]), base_sig(d["IV"])):
        return "S"
    if sig in (base_sig(d["V"]), base_sig(d["vii"])):
        return "D"
    # mimo diatoniku: typicky dominantní napětí
    return "D"

def melody_fits_chord(mel_pc: Optional[str], ch: ChordSpec) -> bool:
    if mel_pc is None:
        return True
    return mel_pc in chord_tones_pcs(ch)

def semitone(pc: str) -> int:
    return PC_TO_SEMITONE[pc]

def add_semitones(pc: str, n: int) -> str:
    return SEMITONE_TO_PC[(semitone(pc) + n) % 12]

def secondary_dominant_of(target_root: str) -> ChordSpec:
    # V/target
    v_root = add_semitones(target_root, 7)
    return ChordSpec(v_root, "dom", True)

def tritone_sub_of_dom(ch: ChordSpec) -> Optional[ChordSpec]:
    if ch.quality != "dom" or not ch.has7:
        return None
    # tritone: +6
    return ChordSpec(add_semitones(ch.root_pc, 6), "dom", True, ch.ext, ch.slash_bass_pc)

def expand_or_reduce_color(
    ch: ChordSpec,
    mel: Optional[str],
    rng: random.Random,
    p_make_triad: float,
    p_add_ext: float,
) -> ChordSpec:
    """
    Rozšíření / zjednodušení – ale vždy kytarově.
    Přidává 6/9/11/13 jen konzervativně a často jen pokud melodie "prosí" o extension.
    """
    c = ch

    # někdy shodit 7 → triáda
    if c.has7 and rng.random() < p_make_triad:
        c = ChordSpec(c.root_pc, c.quality, False, None, c.slash_bass_pc)

    # někdy přidat extension
    if rng.random() < p_add_ext:
        # melodie jako "hint"
        if mel is not None:
            r = semitone(c.root_pc)
            m = semitone(mel)
            interval = (m - r) % 12

            ext = None
            # durová/minorová logika: 2->9, 5->11/sus4, 9->6/13
            if interval == 2:
                ext = "9" if c.quality == "dom" else "add9"
            elif interval == 5:
                ext = "sus4" if c.quality == "dom" else "11"
            elif interval == 9:
                ext = "13" if c.quality == "dom" else "6"

            if ext:
                c = ChordSpec(c.root_pc, c.quality, c.has7, ext, c.slash_bass_pc)

    return make_guitar_friendly(c)

# ----------------------------
# Melody extraction with attacks (for rhythm-friendly chord changes)
# ----------------------------
def get_divisions(part_measure: ET.Element) -> int:
    attr = part_measure.find("attributes")
    if attr is None:
        return 1
    div = attr.findtext("divisions")
    return int(div) if div else 1

def extract_melody_profile_from_measure(measure: ET.Element, divisions: int) -> Tuple[List[Optional[str]], List[bool]]:
    """
    Vrátí:
      - pcs_per_beat[4]
      - attack_per_beat[4] (True když na této době začne nota; rest = False)
    Assumes 4/4.
    """
    pcs: List[Optional[str]] = []
    attacks = [False, False, False, False]

    t_div = 0
    for n in measure.findall("note"):
        dur = int(n.findtext("duration") or "0")
        beat_index = (t_div // divisions) if divisions > 0 else 0
        pc = parse_pitch_to_pc(n)

        # attack jen pokud je to nota (ne rest) a začíná přesně na beat boundary
        if pc is not None and t_div % divisions == 0 and 0 <= beat_index < 4:
            attacks[beat_index] = True

        q = max(1, dur // divisions) if divisions > 0 else 1
        pcs.extend([pc] * q)
        t_div += max(dur, 0)

    if len(pcs) < 4:
        pcs.extend([None] * (4 - len(pcs)))
    return pcs[:4], attacks

def extract_harmony_chords_from_measure(measure: ET.Element) -> List[ChordSpec]:
    hs = measure.findall("harmony")

    def off(h: ET.Element) -> int:
        return int(h.findtext("offset") or "0")

    def harmony_to_text(h: ET.Element) -> str:
        # root
        root_step = h.findtext("root/root-step") or "C"
        root_alter = int(h.findtext("root/root-alter") or "0")

        if root_alter == -1:
            root_pc = f"{root_step}b"
        elif root_alter == 1:
            root_pc = f"{root_step}#"
        else:
            root_pc = root_step

        # kind
        kind_el = h.find("kind")
        kind_text_attr = ""
        kind_value = ""

        if kind_el is not None:
            kind_text_attr = (kind_el.attrib.get("text") or "").strip()
            kind_value = (kind_el.text or "").strip()

        # suffix without root
        suffix = kind_text_attr

        if not suffix:
            if kind_value == "major":
                suffix = ""
            elif kind_value == "minor":
                suffix = "m"
            elif kind_value == "dominant":
                suffix = "7"
            elif kind_value == "major-seventh":
                suffix = "maj7"
            elif kind_value == "minor-seventh":
                suffix = "m7"
            elif kind_value == "half-diminished":
                suffix = "m7b5"
            elif kind_value == "diminished":
                suffix = "dim"
            else:
                suffix = ""

        return f"{root_pc}{suffix}"

    hs.sort(key=off)

    chords: List[ChordSpec] = []
    for h in hs[:4]:
        txt = harmony_to_text(h)
        chords.append(parse_chord_text(txt))

    while len(chords) < 4:
        chords.append(parse_chord_text("Cmaj7"))

    return chords[:4]


# ----------------------------
# Register / voicing continuity helpers
# ----------------------------
def chord_span_profile(
    ch: ChordSpec,
    base_octave: int = 3,
    min_bass_midi: int = 43,
    max_top_midi: int = 64,
) -> Tuple[int, float, int]:
    """
    Return a compact voicing profile:
      (bass_midi, center_of_mass, top_midi)
    using the same safe voicing logic as export.
    """
    pcs = chord_tones_pcs(make_guitar_friendly(ch))
    midis = choose_voicing_midis_bass_safe(
        pcs,
        base_octave=base_octave,
        force_bass_pc=ch.slash_bass_pc,
        min_bass_midi=min_bass_midi,
        max_top_midi=max_top_midi,
    )
    bass = min(midis)
    top = max(midis)
    center = sum(midis) / len(midis)
    return bass, center, top

def is_non_diatonic_tension(ch: ChordSpec, key_pc: str) -> bool:
    """
    True for chords outside the core diatonic collection or for strong
    dominant-tension colors where somewhat larger position shifts are acceptable.
    """
    di = diatonic_chords_in_key(key_pc)
    base_sig = _sig(ChordSpec(ch.root_pc, ch.quality, ch.has7, None, None))
    di_sigs = {_sig(ChordSpec(v.root_pc, v.quality, v.has7, None, None)) for v in di.values()}
    if base_sig not in di_sigs:
        return True
    if ch.quality == "dom" and ch.root_pc != di["V"].root_pc:
        return True
    return False

def register_transition_penalty(
    prev: ChordSpec,
    cur: ChordSpec,
    key_pc: str,
    base_octave: int = 3,
    min_bass_midi: int = 43,
    max_top_midi: int = 64,
    bass_jump_soft: int = 5,
    bass_jump_hard: int = 9,
    center_jump_soft: int = 4,
    center_jump_hard: int = 8,
) -> float:
    """
    Penalize large register / bass jumps between adjacent chords.
    Small motions are fine, larger motions are increasingly discouraged.
    Non-diatonic dominants / substitutions are allowed somewhat larger leaps.
    """
    prev_bass, prev_center, prev_top = chord_span_profile(
        prev, base_octave, min_bass_midi, max_top_midi
    )
    cur_bass, cur_center, cur_top = chord_span_profile(
        cur, base_octave, min_bass_midi, max_top_midi
    )

    bass_jump = abs(cur_bass - prev_bass)
    center_jump = abs(cur_center - prev_center)
    top_jump = abs(cur_top - prev_top)

    relax = 1.0
    if is_non_diatonic_tension(cur, key_pc) or is_non_diatonic_tension(prev, key_pc):
        relax = 1.45

    bass_soft = bass_jump_soft * relax
    bass_hard = bass_jump_hard * relax
    center_soft = center_jump_soft * relax
    center_hard = center_jump_hard * relax

    penalty = 0.0

    if bass_jump > bass_soft:
        penalty += 0.12 + 0.018 * (bass_jump - bass_soft)
    if bass_jump > bass_hard:
        penalty += 0.20 + 0.025 * (bass_jump - bass_hard)

    if center_jump > center_soft:
        penalty += 0.08 + 0.014 * (center_jump - center_soft)
    if center_jump > center_hard:
        penalty += 0.14 + 0.020 * (center_jump - center_hard)

    if top_jump > 10:
        penalty += 0.08 + 0.010 * (top_jump - 10)

    return penalty

# ----------------------------
# "Quantum logical" DP optimizer (amplitudes + interference)
# ----------------------------
def _sig(ch: ChordSpec) -> Tuple[str, str, bool, Optional[str], Optional[str]]:
    return (ch.root_pc, ch.quality, ch.has7, ch.ext, ch.slash_bass_pc)

def generate_candidates(
    original: ChordSpec,
    mel: Optional[str],
    key_pc: str,
    next_original: Optional[ChordSpec],
    allow_secondary: bool = True,
    allow_tritone: bool = True,
) -> List[ChordSpec]:
    """
    Kandidáti jsou primárně postaveni kolem harmonizer akordu.
    Náhrady se nabízejí, ale original má vždy prioritu ve skóre.
    """
    cand: List[ChordSpec] = []

    # vždy original (a jeho triad/7 varianty)
    cand.append(make_guitar_friendly(original))
    cand.append(make_guitar_friendly(ChordSpec(original.root_pc, original.quality, False, original.ext, original.slash_bass_pc)))
    if original.has7 is False:
        cand.append(make_guitar_friendly(ChordSpec(original.root_pc, original.quality, True, original.ext, original.slash_bass_pc)))

    # diatonické pilíře (jen jako fallback)
    di = diatonic_chords_in_key(key_pc)
    cand.extend([make_guitar_friendly(v) for v in di.values()])

    # sekundární dominanty (mimotónální dominanta)
    if allow_secondary and next_original is not None:
        # target ber jako root příštího akordu (ať je to “logické”, ne statistické)
        v_of_next = secondary_dominant_of(next_original.root_pc)
        cand.append(make_guitar_friendly(v_of_next))

        # tritonová substituce k V/next
        if allow_tritone:
            ts = tritone_sub_of_dom(v_of_next)
            if ts:
                cand.append(make_guitar_friendly(ts))

    # tritonová substituce k originálu (pokud je to dom7)
    if allow_tritone:
        ts0 = tritone_sub_of_dom(original)
        if ts0:
            cand.append(make_guitar_friendly(ts0))

    # odstranit duplicitní
    out: List[ChordSpec] = []
    seen = set()
    for c in cand:
        k = _sig(c)
        if k not in seen:
            seen.add(k)
            out.append(c)
    return out

def quantum_choose_progression(
    bars_orig: List[List[ChordSpec]],
    bars_mel: List[List[Optional[str]]],
    bars_attacks: List[List[bool]],
    key_pc: str,
    seed: int = 7,
    prefer_original_bonus: float = 0.55,
    change_penalty: float = 0.28,
    change_penalty_on_attack_weak: float = 0.55,   # hlavně pro beat 2/4
    bad_melody_penalty: float = 0.75,
    reward_resolution_D_to_T: float = 0.65,
    reward_T_to_S: float = 0.18,
    reward_S_to_D: float = 0.22,
    tonic_fatigue_penalty: float = 0.20,
    register_smoothness_weight: float = 1.0,
) -> List[List[ChordSpec]]:
    """
    Globální DP přes všechny beaty.
    Skóre = "amplituda" kompatibility:
      - melodie vs akord
      - funkční tok T/S/D (logický)
      - rytmus změn (ne na melodickém útoku; zvlášť 2/4)
      - preferuje harmonizer akordy, ale dovolí “logické” náhrady
    """
    rng = random.Random(seed)

    # flatten
    seq_orig: List[ChordSpec] = []
    seq_mel: List[Optional[str]] = []
    seq_att: List[bool] = []
    for b in range(len(bars_orig)):
        for i in range(4):
            seq_orig.append(bars_orig[b][i])
            seq_mel.append(bars_mel[b][i])
            seq_att.append(bars_attacks[b][i])

    N = len(seq_orig)
    if N == 0:
        return bars_orig

    # candidates per beat (needs next chord reference)
    cands: List[List[ChordSpec]] = []
    for t in range(N):
        next_ch = seq_orig[t+1] if t+1 < N else None
        cands.append(generate_candidates(seq_orig[t], seq_mel[t], key_pc, next_ch, True, True))

    def beat_score(prev: Optional[ChordSpec], cur: ChordSpec, t: int) -> float:
        s = 0.0
        mel = seq_mel[t]

        # prefer original chord (respect harmonizer)
        if _sig(cur) == _sig(make_guitar_friendly(seq_orig[t])):
            s += prefer_original_bonus

        # melody fit
        if melody_fits_chord(mel, cur):
            s += 1.0
        else:
            s -= bad_melody_penalty

        # discourage too many tonics in a row (if melody allows alternatives)
        if prev is not None:
            if chord_function_TSD(prev, key_pc) == "T" and chord_function_TSD(cur, key_pc) == "T":
                if mel is None or melody_fits_chord(mel, cur):
                    s -= tonic_fatigue_penalty

        # change penalties, stronger if melody attacks (especially beat 2/4)
        if prev is not None and _sig(prev) != _sig(cur):
            s -= change_penalty
            beat_in_bar = t % 4
            if seq_att[t] and beat_in_bar in (1, 3):  # 2nd or 4th beat
                s -= change_penalty_on_attack_weak

        # functional logic (rule-based)
        if prev is not None:
            f_prev = chord_function_TSD(prev, key_pc)
            f_cur = chord_function_TSD(cur, key_pc)

            # allowed logical steps (not forced)
            allowed = {("T","T"),("T","S"),("T","D"),
                       ("S","S"),("S","D"),
                       ("D","D"),("D","T")}
            if (f_prev, f_cur) not in allowed:
                s -= 0.45

            # reward resolutions
            if f_prev == "D" and f_cur == "T":
                s += reward_resolution_D_to_T
            if f_prev == "T" and f_cur == "S":
                s += reward_T_to_S
            if f_prev == "S" and f_cur == "D":
                s += reward_S_to_D

            # prefer close bass/register continuation; allow somewhat larger
            # moves mainly for non-diatonic dominant tension
            s -= register_smoothness_weight * register_transition_penalty(prev, cur, key_pc)

        # "dominanta/subdominanta jen když je možnost":
        # pokud melodie obsahuje leading tone (7) nebo 4, přitlač D/S.
        if mel is not None:
            root = semitone(key_pc)
            mel_st = semitone(mel)
            deg = (mel_st - root) % 12
            func = chord_function_TSD(cur, key_pc)
            # v dur: 11 = 4. stupeň, 10/11? (zjednodušeně) - bereme 5 (subdominantní pocit)
            if deg == 11 and func == "D":  # leading tone
                s += 0.25
            if deg == 5 and func == "S":   # subdominantní (F v C dur)
                s += 0.22

        # malé "kvantové koření": náhodně (ale stabilně) přidej drobný phase-bias
        # (jen aby optimizer nebyl deterministicky stále stejný při stejných datech a seed)
        s += (rng.random() - 0.5) * 0.02
        return s

    # DP
    dp: List[List[Tuple[float, int]]] = []
    dp.append([(beat_score(None, c, 0), -1) for c in cands[0]])

    for t in range(1, N):
        row: List[Tuple[float, int]] = []
        for j, cur in enumerate(cands[t]):
            best = None
            best_i = 0
            for i, prev in enumerate(cands[t-1]):
                sc_prev, _ = dp[t-1][i]
                sc = sc_prev + beat_score(prev, cur, t)
                if best is None or sc > best:
                    best = sc
                    best_i = i
            row.append((float(best), best_i))
        dp.append(row)

    last_j = max(range(len(dp[N-1])), key=lambda j: dp[N-1][j][0])
    seq_out: List[ChordSpec] = [cands[N-1][last_j]]
    j = last_j
    for t in range(N-1, 0, -1):
        _, pj = dp[t][j]
        seq_out.append(cands[t-1][pj])
        j = pj
    seq_out.reverse()

    # post-process: jemné rozšíření/triády (ale stále kytarově)
    # (tady už nepřepisujeme harmonizer brutálně; spíš kolorujeme)
    out_seq: List[ChordSpec] = []
    for t in range(N):
        c = seq_out[t]
        mel = seq_mel[t]
        c = expand_or_reduce_color(c, mel, rng, p_make_triad=0.18, p_add_ext=0.22)
        out_seq.append(c)

    # unflatten
    out: List[List[ChordSpec]] = []
    idx = 0
    for b in range(len(bars_orig)):
        out.append(out_seq[idx:idx+4])
        idx += 4
    return out

# ----------------------------
# Inversions (slash bass) to smooth bass
# ----------------------------
def choose_inversions_for_smooth_bass(
    bars_chords: List[List[ChordSpec]],
    base_octave: int = 3,
) -> List[List[ChordSpec]]:
    prev_bass_midi: Optional[int] = None
    prev_center: Optional[float] = None
    prev_root_pc: Optional[str] = None
    out: List[List[ChordSpec]] = []

    for bar in bars_chords:
        bar_out: List[ChordSpec] = []
        for ch in bar:
            pcs = chord_tones_pcs(ch)
            bass_choices = pcs[:4]

            cand = []
            for bpc in bass_choices:
                candidate = make_guitar_friendly(
                    ChordSpec(ch.root_pc, ch.quality, ch.has7, ch.ext, None if bpc == ch.root_pc else bpc)
                )
                bass, center, top = chord_span_profile(candidate, base_octave)

                score = 0.0
                if prev_bass_midi is not None:
                    score += abs(bass - prev_bass_midi)
                if prev_center is not None:
                    score += 0.55 * abs(center - prev_center)

                # mild hysteresis: avoid needless back-and-forth inversion flipping
                if prev_root_pc == ch.root_pc and bpc == ch.root_pc:
                    score -= 0.15

                cand.append((score, bpc, bass, center))

            if not cand:
                bar_out.append(ch)
                continue

            _, chosen_bpc, chosen_bass, chosen_center = min(cand, key=lambda t: t[0])

            prev_bass_midi = chosen_bass
            prev_center = chosen_center
            prev_root_pc = ch.root_pc

            slash = chosen_bpc if chosen_bpc != ch.root_pc else None
            ch2 = ChordSpec(ch.root_pc, ch.quality, ch.has7, ch.ext, slash)
            ch2 = make_guitar_friendly(ch2)
            bar_out.append(ch2)
        out.append(bar_out)
    return out

def enforce_final_cadence(
    bars: List[List[ChordSpec]],
    prefer: str = "Cmaj7",
) -> List[List[ChordSpec]]:
    if not bars:
        return bars
    last_bar = bars[-1][:]
    last_bar[-1] = make_guitar_friendly(parse_chord_text(prefer))
    bars[-1] = last_bar
    return bars

def sustain_last_bar_to_end(bars: List[List[ChordSpec]]) -> List[List[ChordSpec]]:
    if not bars:
        return bars
    last = bars[-1][:]
    if len(last) != 4:
        return bars

    last_change_idx = 0
    for i in range(1, 4):
        if _sig(last[i]) != _sig(last[i - 1]):
            last_change_idx = i

    hold = last[last_change_idx]
    for i in range(last_change_idx, 4):
        last[i] = hold

    bars[-1] = last
    return bars

# ----------------------------
# MusicXML writing (FRESH)
# ----------------------------
def _kind_for(ch: ChordSpec) -> str:
    if ch.quality == "maj" and ch.has7:
        return "major-seventh"
    if ch.quality == "min" and ch.has7:
        return "minor-seventh"
    if ch.quality == "dom" and ch.has7:
        return "dominant"
    if ch.quality == "hdim" and ch.has7:
        return "half-diminished"
    if ch.quality == "min":
        return "minor"
    return "major"

def build_harmony_element(ch: ChordSpec, offset_divisions: Optional[int]) -> ET.Element:
    h = ET.Element("harmony")

    root = ET.SubElement(h, "root")
    step, alter = PC_TO_STEP_ALTER[ch.root_pc]
    ET.SubElement(root, "root-step").text = step
    if alter != 0:
        ET.SubElement(root, "root-alter").text = str(alter)

    if ch.slash_bass_pc:
        bass = ET.SubElement(h, "bass")
        bstep, balter = PC_TO_STEP_ALTER[ch.slash_bass_pc]
        ET.SubElement(bass, "bass-step").text = bstep
        if balter != 0:
            ET.SubElement(bass, "bass-alter").text = str(balter)

    kind = ET.SubElement(h, "kind")
    kind.text = _kind_for(ch)

    suf = kind_text_suffix(ch)
    if suf:
        kind.set("text", suf)

    ET.SubElement(h, "staff").text = "1"

    if offset_divisions is not None and offset_divisions > 0:
        ET.SubElement(h, "offset").text = str(offset_divisions)

    ET.SubElement(h, "harmony-text").text = chord_text_for_display(ch)
    return h

def strip_harmony_from_measure(measure: ET.Element) -> None:
    for h in list(measure.findall("harmony")):
        measure.remove(h)

def _note_start_times_in_divisions(measure: ET.Element) -> List[Tuple[int, ET.Element]]:
    notes = measure.findall("note")
    t = 0
    out: List[Tuple[int, ET.Element]] = []
    for n in notes:
        out.append((t, n))
        dur = int(n.findtext("duration") or "0")
        t += max(dur, 0)
    return out

def insert_harmony_into_measure(measure: ET.Element, chords_4: List[ChordSpec], divisions: int) -> None:
    strip_harmony_from_measure(measure)

    note_starts = _note_start_times_in_divisions(measure)

    change_beats = [0]
    for i in range(1, 4):
        if _sig(chords_4[i]) != _sig(chords_4[i - 1]):
            change_beats.append(i)

    def note_at_time(target_time: int) -> Optional[ET.Element]:
        for st, n in note_starts:
            if st == target_time:
                return n
        return None

    for beat_i in change_beats:
        target_time = beat_i * divisions
        anchor = note_at_time(target_time)

        if anchor is not None:
            h = build_harmony_element(chords_4[beat_i], offset_divisions=None)
            idx = list(measure).index(anchor)
            measure.insert(idx, h)
        else:
            h = build_harmony_element(chords_4[beat_i], offset_divisions=target_time)
            children = list(measure)
            insert_at = 0
            for k, el in enumerate(children):
                if el.tag == "note":
                    insert_at = k
                    break
                insert_at = k + 1
            measure.insert(insert_at, h)

def _set_type_and_dots(note: ET.Element, beats_len: int) -> None:
    for el in list(note.findall("type")):
        note.remove(el)
    for el in list(note.findall("dot")):
        note.remove(el)

    if beats_len == 4:
        ET.SubElement(note, "type").text = "whole"
    elif beats_len == 2:
        ET.SubElement(note, "type").text = "half"
    elif beats_len == 3:
        ET.SubElement(note, "type").text = "half"
        ET.SubElement(note, "dot")
    else:
        ET.SubElement(note, "type").text = "quarter"

def build_p2_measure_from_chords(
    measure_number: str,
    divisions: int,
    chords_4: List[ChordSpec],
    base_octave: int = 3,
    min_bass_midi: int = 43,
    max_top_midi: int = 64,
) -> ET.Element:
    m = ET.Element("measure", number=measure_number)

    spans: List[Tuple[int, int, ChordSpec]] = []
    i = 0
    while i < 4:
        j = i + 1
        while j < 4 and _sig(chords_4[j]) == _sig(chords_4[i]):
            j += 1
        spans.append((i, j - i, chords_4[i]))
        i = j

    for (_, length_beats, ch0) in spans:
        ch = make_guitar_friendly(ch0)
        dur = length_beats * divisions

        pcs = chord_tones_pcs(ch)
        midis = choose_voicing_midis_bass_safe(
            pcs,
            base_octave=base_octave,
            force_bass_pc=ch.slash_bass_pc,
            min_bass_midi=min_bass_midi,
            max_top_midi=max_top_midi,
        )
        pitches = [midi_to_step_alter_oct(m_) for m_ in midis]

        for v_i, (step, alter, octv) in enumerate(pitches):
            note = ET.Element("note")
            if v_i > 0:
                ET.SubElement(note, "chord")

            pitch = ET.SubElement(note, "pitch")
            ET.SubElement(pitch, "step").text = step
            if alter != 0:
                ET.SubElement(pitch, "alter").text = str(alter)
            ET.SubElement(pitch, "octave").text = str(octv)

            ET.SubElement(note, "duration").text = str(dur)
            ET.SubElement(note, "voice").text = "1"
            ET.SubElement(note, "staff").text = "1"
            _set_type_and_dots(note, length_beats)
            m.append(note)

    return m

def build_fresh_musicxml(
    original_root: ET.Element,
    original_p1_part: ET.Element,
    optimized_bars: List[List[ChordSpec]],
    divisions: int,
    title: str = "Quantum Harmonizer (Optimized)",
    composer: str = "Josef P.",
    p2_base_octave: int = 3,
    p2_min_bass_midi: int = 43,
    p2_max_top_midi: int = 64,
) -> ET.Element:
    score = ET.Element("score-partwise", version="3.1")

    work = ET.SubElement(score, "work")
    ET.SubElement(work, "work-title").text = title

    identification = ET.SubElement(score, "identification")
    creator = ET.SubElement(identification, "creator", type="composer")
    creator.text = composer

    part_list = ET.SubElement(score, "part-list")
    sp1 = ET.SubElement(part_list, "score-part", id="P1")
    ET.SubElement(sp1, "part-name").text = "Melody"
    sp2 = ET.SubElement(part_list, "score-part", id="P2")
    ET.SubElement(sp2, "part-name").text = "Chords (LH Bass)"

    p1 = ET.SubElement(score, "part", id="P1")
    orig_measures = original_p1_part.findall("measure")
    n = min(len(orig_measures), len(optimized_bars))

    for i in range(n):
        m = copy.deepcopy(orig_measures[i])
        strip_harmony_from_measure(m)
        insert_harmony_into_measure(m, optimized_bars[i], divisions)
        p1.append(m)

    p2 = ET.SubElement(score, "part", id="P2")
    for i in range(n):
        mnum = orig_measures[i].attrib.get("number", str(i + 1))
        m2 = build_p2_measure_from_chords(
            measure_number=mnum,
            divisions=divisions,
            chords_4=optimized_bars[i],
            base_octave=p2_base_octave,
            min_bass_midi=p2_min_bass_midi,
            max_top_midi=p2_max_top_midi,
        )

        if i == 0:
            attrs = ET.Element("attributes")
            ET.SubElement(attrs, "divisions").text = str(divisions)

            orig_attr = orig_measures[0].find("attributes")
            if orig_attr is not None:
                key = orig_attr.find("key")
                time = orig_attr.find("time")
                if key is not None:
                    attrs.append(copy.deepcopy(key))
                if time is not None:
                    attrs.append(copy.deepcopy(time))

            clef = ET.SubElement(attrs, "clef")
            ET.SubElement(clef, "sign").text = "F"
            ET.SubElement(clef, "line").text = "4"
            m2.insert(0, attrs)

        p2.append(m2)

    return score

# ----------------------------
# Main optimize
# ----------------------------
def optimize_musicxml_fresh(
    in_path: str,
    out_path: str,
    seed: int = 7,
    enforce_cadence: bool = True,
    cadence: str = "Cmaj7",  # or "G7"
    do_inversions: bool = True,
    p2_base_octave: int = 3,
    p2_min_bass_midi: int = 43,
    p2_max_top_midi: int = 64,
):
    tree = ET.parse(in_path)
    root = tree.getroot()

    parts = {p.attrib.get("id"): p for p in root.findall("part")}
    if "P1" not in parts:
        raise ValueError("Expected part P1 (melody) in input MusicXML.")

    p1_in = parts["P1"]
    m1_list = p1_in.findall("measure")
    if not m1_list:
        raise ValueError("No measures found in P1.")

    divisions = get_divisions(m1_list[0])

    bars_mel: List[List[Optional[str]]] = []
    bars_att: List[List[bool]] = []
    bars_chords: List[List[ChordSpec]] = []

    for m in m1_list:
        mel_pcs, attacks = extract_melody_profile_from_measure(m, divisions)
        chs = extract_harmony_chords_from_measure(m)
        bars_mel.append(mel_pcs)
        bars_att.append(attacks)
        bars_chords.append(chs)

    # Key: prefer key signature, else melody heuristic
    key_pc = infer_key_from_key_signature(m1_list[0]) or infer_key_from_melody(bars_mel)

    # 1) QUANTUM-LOGICAL choice (global DP) – but respecting harmonizer chords
    optimized = quantum_choose_progression(
        bars_orig=bars_chords,
        bars_mel=bars_mel,
        bars_attacks=bars_att,
        key_pc=key_pc,
        seed=seed,
    )

    # 2) inversions (slash bass) to smooth bass
    if do_inversions:
        optimized = choose_inversions_for_smooth_bass(optimized, base_octave=p2_base_octave)
    else:
        optimized = [[make_guitar_friendly(c) for c in bar] for bar in optimized]

    # 3) cadence (first)
    if enforce_cadence:
        optimized = enforce_final_cadence(optimized, prefer=cadence)

    # 4) sustain last chord to end (after cadence!)
    optimized = sustain_last_bar_to_end(optimized)

    # 5) export fresh MusicXML
    fresh_root = build_fresh_musicxml(
        original_root=root,
        original_p1_part=p1_in,
        optimized_bars=optimized,
        divisions=divisions,
        title="Quantum Harmonizer (Optimized)",
        composer="Josef P.",
        p2_base_octave=p2_base_octave,
        p2_min_bass_midi=p2_min_bass_midi,
        p2_max_top_midi=p2_max_top_midi,
    )

    ET.ElementTree(fresh_root).write(out_path, encoding="utf-8", xml_declaration=True)
    print(f"Fresh optimized MusicXML saved: {out_path}")

def _default_paths() -> Tuple[str, str]:
    here = Path(__file__).resolve().parent
    project_root = here.parent
    in_path = project_root / "quantum_output.musicxml"
    out_path = project_root / "quantum_output_optimized.musicxml"
    return str(in_path), str(out_path)

if __name__ == "__main__":
    default_in, default_out = _default_paths()

    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", default=default_in)
    parser.add_argument("--out", dest="out_path", default=default_out)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--cadence", type=str, default="Cmaj7")
    parser.add_argument("--no-cadence", action="store_true")
    parser.add_argument("--no-inv", action="store_true")

    parser.add_argument("--p2-oct", type=int, default=3)
    parser.add_argument("--p2-min-bass", type=int, default=43)
    parser.add_argument("--p2-max-top", type=int, default=64)

    args = parser.parse_args()

    optimize_musicxml_fresh(
        in_path=args.in_path,
        out_path=args.out_path,
        seed=args.seed,
        enforce_cadence=not args.no_cadence,
        cadence=args.cadence,
        do_inversions=not args.no_inv,
        p2_base_octave=args.p2_oct,
        p2_min_bass_midi=args.p2_min_bass,
        p2_max_top_midi=args.p2_max_top,
    )