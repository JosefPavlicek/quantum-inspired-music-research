from copy import deepcopy
from typing import Dict, List
import xml.etree.ElementTree as ET
from xml.dom import minidom

from .beat_representation import BeatEvent
from .chord_library import ChordDef, PC_TO_SEMITONE

PITCH_CLASS_TO_SEMITONE_XML = {
    ("C", -1): 11,  # Cb
    ("C", 0): 0,
    ("C", 1): 1,    # C#

    ("D", -1): 1,   # Db
    ("D", 0): 2,
    ("D", 1): 3,    # D#

    ("E", -1): 3,   # Eb
    ("E", 0): 4,
    ("E", 1): 5,    # E#

    ("F", -1): 4,   # Fb
    ("F", 0): 5,
    ("F", 1): 6,    # F#

    ("G", -1): 6,   # Gb
    ("G", 0): 7,
    ("G", 1): 8,    # G#

    ("A", -1): 8,   # Ab
    ("A", 0): 9,
    ("A", 1): 10,   # A#

    ("B", -1): 10,  # Bb
    ("B", 0): 11,
    ("B", 1): 0,    # B#
}

SEMITONE_TO_STEP_ALTER = {
    0: ("C", 0),
    1: ("D", -1),   # Db
    2: ("D", 0),
    3: ("E", -1),   # Eb
    4: ("E", 0),
    5: ("F", 0),
    6: ("G", -1),   # Gb
    7: ("G", 0),
    8: ("A", -1),   # Ab
    9: ("A", 0),
    10: ("B", -1),  # Bb
    11: ("B", 0),
}

NOTE_TO_SEMITONE = {
    "C": 0, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5,
    "Gb": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11
}


def split_chord_name(chord_name: str):
    """
    Returns:
    root_pc, kind_value, display_suffix
    Example:
    C      -> ("C", "major", "")
    Dm     -> ("D", "minor", "m")
    Cmaj7  -> ("C", "major-seventh", "maj7")
    Dm7    -> ("D", "minor-seventh", "m7")
    G7     -> ("G", "dominant", "7")
    Bdim   -> ("B", "diminished", "dim")
    Bm7b5  -> ("B", "half-diminished", "m7b5")
    """
    if chord_name.endswith("maj7"):
        return chord_name[:-4], "major-seventh", "maj7"
    if chord_name.endswith("m7b5"):
        return chord_name[:-4], "half-diminished", "m7b5"
    if chord_name.endswith("m7"):
        return chord_name[:-2], "minor-seventh", "m7"
    if chord_name.endswith("7"):
        return chord_name[:-1], "dominant", "7"
    if chord_name.endswith("dim"):
        return chord_name[:-3], "diminished", "dim"
    if chord_name.endswith("m"):
        return chord_name[:-1], "minor", "m"
    return chord_name, "major", ""


def add_harmony_symbol(parent, chord_name: str):
    root_pc, kind_value, display_suffix = split_chord_name(chord_name)

    harmony = ET.SubElement(parent, "harmony")

    root = ET.SubElement(harmony, "root")

    if len(root_pc) >= 2 and root_pc[1] in ("b", "#"):
        root_step = root_pc[0]
        alter = -1 if root_pc[1] == "b" else 1
    else:
        root_step = root_pc[0]
        alter = 0

    ET.SubElement(root, "root-step").text = root_step
    if alter != 0:
        ET.SubElement(root, "root-alter").text = str(alter)

    kind = ET.SubElement(harmony, "kind")
    kind.set("text", display_suffix)
    kind.text = kind_value


def remove_existing_harmony_symbols(part):
    for measure in part.findall("measure"):
        for el in list(measure):
            if el.tag == "harmony":
                measure.remove(el)

def build_harmony_element(chord_name: str) -> ET.Element:
    harmony = ET.Element("harmony")

    root_pc, kind_value, display_suffix = split_chord_name(chord_name)

    root = ET.SubElement(harmony, "root")

    if len(root_pc) >= 2 and root_pc[1] in ("b", "#"):
        root_step = root_pc[0]
        alter = -1 if root_pc[1] == "b" else 1
    else:
        root_step = root_pc[0]
        alter = 0

    ET.SubElement(root, "root-step").text = root_step
    if alter != 0:
        ET.SubElement(root, "root-alter").text = str(alter)

    kind = ET.SubElement(harmony, "kind")
    kind.set("text", display_suffix)
    kind.text = kind_value

    return harmony

def insert_harmony_symbols_by_offsets(
    melody_part,
    events: List[BeatEvent],
    chords: List[str],
):
    """
    Insert harmony symbols into the melody part, timed by the harmonic beat grid.

    The symbols remain above the melody staff, but their positions are computed
    from beat locations in the harmonizer output. Offsets are absolute from the
    beginning of the measure, which prevents missing or merged chord symbols
    during half notes / whole notes in the melody.
    """
    bars = group_events_by_bar(events)
    measures = melody_part.findall("measure")

    chord_global_index = 0

    current_divisions = 1
    current_beats = 4
    current_beat_type = 4

    for bar_index, measure in enumerate(measures):
        bar_events = bars.get(bar_index, [])
        if not bar_events:
            continue

        # carry attributes forward
        attributes = measure.find("attributes")
        if attributes is not None:
            div_tag = attributes.find("divisions")
            if div_tag is not None and div_tag.text:
                current_divisions = int(div_tag.text)

            time_tag = attributes.find("time")
            if time_tag is not None:
                beats_tag = time_tag.find("beats")
                beat_type_tag = time_tag.find("beat-type")
                if beats_tag is not None and beat_type_tag is not None:
                    current_beats = int(beats_tag.text)
                    current_beat_type = int(beat_type_tag.text)

        duration_per_beat = int(current_divisions * (4 / current_beat_type))

        # harmony symbols stay above melody line,
        # so insert them before the first note in the measure
        insert_index = None
        for i, el in enumerate(measure):
            if el.tag == "note":
                insert_index = i
                break

        if insert_index is None:
            insert_index = len(measure)

        harmony_elements = []

        for local_idx, ev in enumerate(bar_events):
            chord_name = chords[chord_global_index + local_idx]
            harmony = build_harmony_element(chord_name)

            beat_start = ev.beat_in_bar * duration_per_beat

            # IMPORTANT:
            # offset must be absolute from start of measure, not relative delta
            if beat_start > 0:
                offset = ET.SubElement(harmony, "offset")
                offset.text = str(beat_start)

            harmony_elements.append(harmony)

        # insert in reverse so final XML order stays chronological
        for harmony in reversed(harmony_elements):
            measure.insert(insert_index, harmony)

        chord_global_index += len(bar_events)

def set_measure_key_to_c(measure):
    attributes = measure.find("attributes")
    if attributes is None:
        attributes = ET.Element("attributes")
        measure.insert(0, attributes)

    key = attributes.find("key")
    if key is None:
        key = ET.SubElement(attributes, "key")

    fifths = key.find("fifths")
    if fifths is None:
        fifths = ET.SubElement(key, "fifths")
    fifths.text = "0"

    mode = key.find("mode")
    if mode is None:
        mode = ET.SubElement(key, "mode")
    mode.text = "major"
def normalize_all_keys_to_c(part):
    measures = part.findall("measure")
    current_has_key = False
    for i, measure in enumerate(measures):
        attributes = measure.find("attributes")
        if attributes is not None and attributes.find("key") is not None:
            current_has_key = True
            set_measure_key_to_c(measure)
        elif i == 0 and not current_has_key:
            set_measure_key_to_c(measure)
    
def transpose_pitch_element(pitch_elem, semitone_shift: int):
    step = pitch_elem.find("step").text
    alter_tag = pitch_elem.find("alter")
    octave = int(pitch_elem.find("octave").text)

    alter = int(alter_tag.text) if alter_tag is not None else 0

    key = (step, alter)
    if key not in PITCH_CLASS_TO_SEMITONE_XML:
        raise ValueError(f"Unsupported pitch spelling in MusicXML: step={step}, alter={alter}")

    midi = 12 * (octave + 1) + PITCH_CLASS_TO_SEMITONE_XML[key]
    new_midi = midi + semitone_shift

    new_step, new_alter, new_octave = midi_to_step_alter_octave(new_midi)

    pitch_elem.find("step").text = new_step

    existing_alter = pitch_elem.find("alter")
    if new_alter != 0:
        if existing_alter is None:
            existing_alter = ET.SubElement(pitch_elem, "alter")
        existing_alter.text = str(new_alter)
    else:
        if existing_alter is not None:
            pitch_elem.remove(existing_alter)

    pitch_elem.find("octave").text = str(new_octave)


def transpose_melody_part_in_place(melody_part, semitone_shift: int):
    for measure in melody_part.findall("measure"):
        for note in measure.findall("note"):
            if note.find("rest") is not None:
                continue
            pitch = note.find("pitch")
            if pitch is not None:
                transpose_pitch_element(pitch, semitone_shift)


def prettify_xml(elem):
    rough_string = ET.tostring(elem, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def midi_to_step_alter_octave(midi: int):
    pitch_class = midi % 12
    octave = (midi // 12) - 1
    step, alter = SEMITONE_TO_STEP_ALTER[pitch_class]
    return step, alter, octave


def pc_to_midi(pc: str, octave: int) -> int:
    return 12 * (octave + 1) + PC_TO_SEMITONE[pc]


def chord_to_midis(chord: ChordDef, base_octave: int = 3) -> List[int]:
    """
    Build ascending chord tones from the root so the written chord
    is in root position, not scrambled across the same octave.
    Example:
    Am7 -> A3 C4 E4 G4
    """
    root_midi = 12 * (base_octave + 1) + NOTE_TO_SEMITONE[chord.root]
    mids = [root_midi]

    prev = root_midi
    for pc in chord.tones[1:]:
        target_pc = NOTE_TO_SEMITONE[pc]
        cand = 12 * (base_octave + 1) + target_pc

        while cand <= prev:
            cand += 12

        mids.append(cand)
        prev = cand

    return mids


def add_pitch(parent, midi: int):
    step, alter, octave = midi_to_step_alter_octave(midi)
    pitch = ET.SubElement(parent, "pitch")
    ET.SubElement(pitch, "step").text = step
    if alter != 0:
        ET.SubElement(pitch, "alter").text = str(alter)
    ET.SubElement(pitch, "octave").text = str(octave)


def note_type_from_beat_type(beat_type: int) -> str:
    mapping = {
        1: "whole",
        2: "half",
        4: "quarter",
        8: "eighth",
        16: "16th",
    }
    return mapping.get(beat_type, "quarter")


def add_chord_note_group(measure, chord_midis: List[int], duration: int, note_type: str):
    first = True
    for midi in chord_midis:
        note = ET.SubElement(measure, "note")
        if not first:
            ET.SubElement(note, "chord")
        add_pitch(note, midi)
        ET.SubElement(note, "duration").text = str(duration)
        ET.SubElement(note, "voice").text = "1"
        ET.SubElement(note, "type").text = note_type
        first = False


def group_events_by_bar(events: List[BeatEvent]) -> Dict[int, List[BeatEvent]]:
    bars: Dict[int, List[BeatEvent]] = {}
    for ev in events:
        bars.setdefault(ev.bar_index, []).append(ev)
    return bars


def parse_measure_attributes(measure):
    divisions = 1
    beats = 4
    beat_type = 4

    attributes = measure.find("attributes")
    if attributes is not None:
        div_tag = attributes.find("divisions")
        if div_tag is not None and div_tag.text:
            divisions = int(div_tag.text)

        time_tag = attributes.find("time")
        if time_tag is not None:
            beats_tag = time_tag.find("beats")
            beat_type_tag = time_tag.find("beat-type")
            if beats_tag is not None and beat_type_tag is not None:
                beats = int(beats_tag.text)
                beat_type = int(beat_type_tag.text)

    return divisions, beats, beat_type


def ensure_leading_rests_for_pickup(measure) -> int:
    """
    If the first measure is incomplete (anacrusis), pad the missing time
    with explicit rests at the beginning so the melody starts on the correct beat.

    Returns:
        number of inserted beat-rests
    """
    divisions, beats, beat_type = parse_measure_attributes(measure)
    duration_per_beat = int(divisions * (4 / beat_type))
    expected_duration = beats * duration_per_beat

    actual_duration = 0
    for el in measure:
        if el.tag in ("note", "forward"):
            dur = el.find("duration")
            if dur is not None and dur.text:
                actual_duration += int(dur.text)

    missing_duration = expected_duration - actual_duration
    if missing_duration <= 0 or duration_per_beat <= 0:
        return 0
    if missing_duration % duration_per_beat != 0:
        return 0

    rest_count = missing_duration // duration_per_beat

    insert_index = None
    first_note = None
    for i, el in enumerate(measure):
        if el.tag == "note":
            insert_index = i
            first_note = el
            break
    if insert_index is None:
        insert_index = len(measure)

    rest_type = note_type_from_beat_type(beat_type)

    # převezmi voice/staff jen pokud v původní melodii opravdu existují
    template_voice = None
    template_staff = None

    if first_note is not None:
        voice_tag = first_note.find("voice")
        if voice_tag is not None and voice_tag.text:
            template_voice = voice_tag.text

        staff_tag = first_note.find("staff")
        if staff_tag is not None and staff_tag.text:
            template_staff = staff_tag.text

    for offset in range(rest_count):
        rest_note = ET.Element("note")
        ET.SubElement(rest_note, "rest")
        ET.SubElement(rest_note, "duration").text = str(duration_per_beat)

        if template_voice is not None:
            ET.SubElement(rest_note, "voice").text = template_voice
        if template_staff is not None:
            ET.SubElement(rest_note, "staff").text = template_staff

        ET.SubElement(rest_note, "type").text = rest_type
        measure.insert(insert_index + offset, rest_note)

    return rest_count


def clone_measure_attributes_for_harmony(src_measure, dst_measure, add_bass_clef: bool = False):
    src_attrs = src_measure.find("attributes")
    if src_attrs is None:
        return

    dst_attrs = ET.SubElement(dst_measure, "attributes")

    for child in src_attrs:
        if child.tag in ("clef", "key"):
            continue
        dst_attrs.append(deepcopy(child))

    key = ET.SubElement(dst_attrs, "key")
    ET.SubElement(key, "fifths").text = "0"
    ET.SubElement(key, "mode").text = "major"

    if add_bass_clef:
        clef = ET.SubElement(dst_attrs, "clef")
        ET.SubElement(clef, "sign").text = "F"
        ET.SubElement(clef, "line").text = "4"

def write_musicxml_preserve_melody(
    input_xml_path: str,
    events: List[BeatEvent],
    chords: List[str],
    chord_pool: Dict[str, ChordDef],
    out_path: str,
    title: str = "Advanced Quantum Optimizer Output",
    composer: str = "Josef P.",
    chord_base_octave: int = 3,
    semitone_shift_to_c: int = 0,
):
    if len(events) != len(chords):
        raise ValueError("events and chords must have the same length")

    tree = ET.parse(input_xml_path)
    root = tree.getroot()

    work = root.find("work")
    if work is None:
        work = ET.SubElement(root, "work")
    work_title = work.find("work-title")
    if work_title is None:
        work_title = ET.SubElement(work, "work-title")
    work_title.text = title

    identification = root.find("identification")
    if identification is None:
        identification = ET.SubElement(root, "identification")
    creator = None
    for c in identification.findall("creator"):
        if c.attrib.get("type") == "composer":
            creator = c
            break
    if creator is None:
        creator = ET.SubElement(identification, "creator", {"type": "composer"})
    creator.text = composer

    part_list = root.find("part-list")
    if part_list is None:
        raise ValueError("No <part-list> found in input XML.")

    for score_part in list(part_list.findall("score-part")):
        if score_part.attrib.get("id") == "P2":
            part_list.remove(score_part)

    for part in list(root.findall("part")):
        if part.attrib.get("id") == "P2":
            root.remove(part)

    score_part2 = ET.SubElement(part_list, "score-part", id="P2")
    ET.SubElement(score_part2, "part-name").text = "Harmony"

    original_part = root.find("part")
    if original_part is None:
        raise ValueError("No melody <part> found in input XML.")

    transpose_melody_part_in_place(original_part, semitone_shift_to_c)
    remove_existing_harmony_symbols(original_part)
    normalize_all_keys_to_c(original_part)

    original_measures = original_part.findall("measure")
    first_measure_was_padded = False

    if original_measures:
        inserted_count = ensure_leading_rests_for_pickup(original_measures[0])
        first_measure_was_padded = inserted_count > 0

        if first_measure_was_padded and "implicit" in original_measures[0].attrib:
            del original_measures[0].attrib["implicit"]

    insert_harmony_symbols_by_offsets(original_part, events, chords)

    harmony_part = ET.SubElement(root, "part", id="P2")

    bars = group_events_by_bar(events)
    chord_idx = 0

    for bar_index, original_measure in enumerate(original_measures):
        measure_number = original_measure.attrib.get("number", str(bar_index + 1))
        harmony_measure = ET.SubElement(harmony_part, "measure", number=measure_number)

        clone_measure_attributes_for_harmony(
            src_measure=original_measure,
            dst_measure=harmony_measure,
            add_bass_clef=(bar_index == 0),
        )

        divisions, beats, beat_type = parse_measure_attributes(original_measure)
        duration_per_beat = int(divisions * (4 / beat_type))
        note_type = note_type_from_beat_type(beat_type)

        bar_events = bars.get(bar_index, [])
        if not bar_events:
            continue

        for _ in bar_events:
            chord_name = chords[chord_idx]
            chord_def = chord_pool[chord_name]
            chord_midis = chord_to_midis(chord_def, base_octave=chord_base_octave)

            add_chord_note_group(
                measure=harmony_measure,
                chord_midis=chord_midis,
                duration=duration_per_beat,
                note_type=note_type,
            )
            chord_idx += 1

    xml_text = prettify_xml(root)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml_text)