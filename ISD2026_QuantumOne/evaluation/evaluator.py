#!/usr/bin/env python3
"""
AQH evaluator.py

Beat-level evaluator for Advanced Quantum Harmonizer outputs.

Supported:
- standard MusicXML with <harmony>
- raw outputs with beat-level harmony and optional <offset>
- optimized outputs with reduced or restructured harmony changes
- reference comparison against original harmony stored in MusicLibrary

Current structural metrics:
- num_measures
- beats_per_measure
- num_beats
- num_harmony_events
- num_harmonic_segments
- chord_density_per_measure
- avg_chord_duration_beats
- redundancy_ratio
- avg_bass_jump_semitones
- segment_length_std

Additional reference-based metrics:
- reference_file
- reference_found
- reference_num_harmony_events
- reference_num_harmonic_segments
- exact_chord_match_ratio
- functional_agreement_ratio
- harmonic_similarity_ratio
- final_function_match
"""

from __future__ import annotations

import argparse
import csv
import glob
import re
import statistics
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple, Set


@dataclass
class HarmonyEvent:
    time_beats: float
    measure_number: int
    symbol: str
    root: str
    bass: str
    kind_raw: str
    kind_text: str


@dataclass
class EvaluationResult:
    file: str
    num_measures: int
    beats_per_measure: int
    num_beats: int
    num_harmony_events: int
    num_harmonic_segments: int
    chord_density_per_measure: float
    avg_chord_duration_beats: float
    redundancy_ratio: float
    avg_bass_jump_semitones: float
    segment_length_std: float
    reference_file: str
    reference_found: int
    reference_num_harmony_events: int
    reference_num_harmonic_segments: int
    exact_chord_match_ratio: float
    functional_agreement_ratio: float
    harmonic_similarity_ratio: float
    final_function_match: float


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


def find_first_child(element: ET.Element, name: str) -> Optional[ET.Element]:
    for child in element:
        if strip_ns(child.tag) == name:
            return child
    return None


def find_all_children(element: ET.Element, name: str) -> List[ET.Element]:
    return [child for child in element if strip_ns(child.tag) == name]


def get_child_text(element: Optional[ET.Element], default: str = "") -> str:
    if element is None or element.text is None:
        return default
    return element.text.strip()


def parse_int(text: str, default: int = 0) -> int:
    try:
        return int(text)
    except Exception:
        return default


def parse_float(text: str, default: float = 0.0) -> float:
    try:
        return float(text)
    except Exception:
        return default


def alter_to_suffix(alter_text: str) -> str:
    if alter_text == "1":
        return "#"
    if alter_text == "-1":
        return "b"
    return ""


def read_pitch_component(parent: Optional[ET.Element], step_name: str, alter_name: str) -> str:
    if parent is None:
        return ""
    step = get_child_text(find_first_child(parent, step_name))
    alter = get_child_text(find_first_child(parent, alter_name))
    if not step:
        return ""
    return f"{step}{alter_to_suffix(alter)}"


def harmony_to_symbol(harmony_el: ET.Element) -> str:
    harmony_text_el = find_first_child(harmony_el, "harmony-text")
    harmony_text = get_child_text(harmony_text_el)
    if harmony_text:
        return harmony_text

    root_el = find_first_child(harmony_el, "root")
    bass_el = find_first_child(harmony_el, "bass")
    kind_el = find_first_child(harmony_el, "kind")

    root = read_pitch_component(root_el, "root-step", "root-alter")
    bass = read_pitch_component(bass_el, "bass-step", "bass-alter")

    kind_text = ""
    if kind_el is not None:
        kind_text = kind_el.attrib.get("text", "").strip()
        if not kind_text:
            kind_text = get_child_text(kind_el)

    symbol = root or "N"
    if kind_text:
        symbol += kind_text
    if bass and bass != root:
        symbol += f"/{bass}"
    return symbol


def harmony_to_components(harmony_el: ET.Element) -> Tuple[str, str, str, str, str]:
    root_el = find_first_child(harmony_el, "root")
    bass_el = find_first_child(harmony_el, "bass")
    kind_el = find_first_child(harmony_el, "kind")

    root = read_pitch_component(root_el, "root-step", "root-alter")
    bass = read_pitch_component(bass_el, "bass-step", "bass-alter")
    if not bass:
        bass = root

    kind_raw = get_child_text(kind_el)
    kind_text = kind_el.attrib.get("text", "").strip() if kind_el is not None else ""

    symbol = harmony_to_symbol(harmony_el)
    return symbol, (root or "N"), (bass or "N"), kind_raw, kind_text


def parse_musicxml(path: str) -> ET.Element:
    try:
        tree = ET.parse(path)
        return tree.getroot()
    except Exception as exc:
        raise RuntimeError(f"Cannot parse MusicXML file '{path}': {exc}") from exc


def get_first_part(root: ET.Element) -> ET.Element:
    for child in root:
        if strip_ns(child.tag) == "part":
            return child
    raise RuntimeError("No <part> found in MusicXML.")


def extract_score_structure(part: ET.Element) -> Tuple[int, int]:
    for measure in find_all_children(part, "measure"):
        attrs = find_first_child(measure, "attributes")
        if attrs is None:
            continue
        time_el = find_first_child(attrs, "time")
        if time_el is None:
            continue
        beats = parse_int(get_child_text(find_first_child(time_el, "beats")), 4)
        beat_type = parse_int(get_child_text(find_first_child(time_el, "beat-type")), 4)
        return beats, beat_type
    return 4, 4


def count_measures(part: ET.Element) -> int:
    return len(find_all_children(part, "measure"))


def extract_harmony_events(part: ET.Element, beats_per_measure: int, beat_type: int) -> List[HarmonyEvent]:
    events: List[HarmonyEvent] = []
    divisions = 1
    measure_index = 0

    for measure in find_all_children(part, "measure"):
        measure_index += 1
        current_div_pos = 0.0

        attrs = find_first_child(measure, "attributes")
        if attrs is not None:
            div_el = find_first_child(attrs, "divisions")
            if div_el is not None:
                divisions = max(1, parse_int(get_child_text(div_el), 1))

        measure_start_beats = (measure_index - 1) * beats_per_measure

        for child in measure:
            tag = strip_ns(child.tag)

            if tag == "harmony":
                offset_el = find_first_child(child, "offset")
                offset_div = parse_float(get_child_text(offset_el), 0.0) if offset_el is not None else 0.0
                abs_div_pos = current_div_pos + offset_div
                abs_time_beats = measure_start_beats + (abs_div_pos / divisions)
                symbol, root, bass, kind_raw, kind_text = harmony_to_components(child)
                events.append(
                    HarmonyEvent(
                        time_beats=abs_time_beats,
                        measure_number=measure_index,
                        symbol=symbol,
                        root=root,
                        bass=bass,
                        kind_raw=kind_raw,
                        kind_text=kind_text,
                    )
                )
            elif tag == "note":
                duration_el = find_first_child(child, "duration")
                current_div_pos += parse_int(get_child_text(duration_el), 0)
            elif tag == "backup":
                duration_el = find_first_child(child, "duration")
                current_div_pos -= parse_int(get_child_text(duration_el), 0)
            elif tag == "forward":
                duration_el = find_first_child(child, "duration")
                current_div_pos += parse_int(get_child_text(duration_el), 0)

    events.sort(key=lambda e: (e.time_beats, e.measure_number))
    return events


def expand_events_to_beat_grid(
    events: List[HarmonyEvent],
    total_beats: int,
) -> Tuple[List[str], List[str], List[str], List[str], List[str]]:
    beat_grid, bass_grid, root_grid, kind_raw_grid, kind_text_grid = [], [], [], [], []
    current_symbol = "N"
    current_bass = "N"
    current_root = "N"
    current_kind_raw = ""
    current_kind_text = ""
    event_index = 0

    for beat in range(total_beats):
        beat_start = float(beat)
        while event_index < len(events) and events[event_index].time_beats <= beat_start + 1e-9:
            current_symbol = events[event_index].symbol
            current_bass = events[event_index].bass
            current_root = events[event_index].root
            current_kind_raw = events[event_index].kind_raw
            current_kind_text = events[event_index].kind_text
            event_index += 1

        beat_grid.append(current_symbol)
        bass_grid.append(current_bass)
        root_grid.append(current_root)
        kind_raw_grid.append(current_kind_raw)
        kind_text_grid.append(current_kind_text)

    return beat_grid, bass_grid, root_grid, kind_raw_grid, kind_text_grid


def compress_segments_with_bass(beat_grid: List[str], bass_grid: List[str]) -> List[Tuple[str, str, int]]:
    if not beat_grid:
        return []

    segments: List[Tuple[str, str, int]] = []
    current_symbol = beat_grid[0]
    current_bass = bass_grid[0]
    length = 1

    for i in range(1, len(beat_grid)):
        if beat_grid[i] == current_symbol and bass_grid[i] == current_bass:
            length += 1
        else:
            segments.append((current_symbol, current_bass, length))
            current_symbol = beat_grid[i]
            current_bass = bass_grid[i]
            length = 1

    segments.append((current_symbol, current_bass, length))
    return segments


_NOTE_TO_PC = {
    "C": 0, "B#": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4, "E#": 5, "F": 5, "F#": 6, "Gb": 6, "G": 7,
    "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11, "Cb": 11,
}


def pitch_to_pc(note_name: str) -> Optional[int]:
    return _NOTE_TO_PC.get(note_name)


def pitch_class_distance(a: str, b: str) -> Optional[int]:
    pa = pitch_to_pc(a)
    pb = pitch_to_pc(b)
    if pa is None or pb is None:
        return None
    diff = abs(pb - pa)
    return min(diff, 12 - diff)


def compute_num_harmonic_segments(segments: List[Tuple[str, str, int]]) -> int:
    return sum(1 for symbol, _bass, _dur in segments if symbol != "N")


def compute_chord_density_per_measure(num_segments: int, num_measures: int) -> float:
    return 0.0 if num_measures <= 0 else num_segments / num_measures


def compute_avg_chord_duration_beats(segments: List[Tuple[str, str, int]]) -> float:
    valid = [dur for symbol, _bass, dur in segments if symbol != "N"]
    return 0.0 if not valid else sum(valid) / len(valid)


def compute_redundancy_ratio(num_beats: int, num_segments: int) -> float:
    return 0.0 if num_segments <= 0 else num_beats / num_segments


def compute_avg_bass_jump_semitones(segments: List[Tuple[str, str, int]]) -> float:
    valid_segments = [(symbol, bass, dur) for symbol, bass, dur in segments if symbol != "N" and bass != "N"]
    if len(valid_segments) < 2:
        return 0.0

    jumps: List[int] = []
    for i in range(len(valid_segments) - 1):
        dist = pitch_class_distance(valid_segments[i][1], valid_segments[i + 1][1])
        if dist is not None:
            jumps.append(dist)

    return 0.0 if not jumps else sum(jumps) / len(jumps)


def compute_segment_length_std(segments: List[Tuple[str, str, int]]) -> float:
    lengths = [dur for symbol, _bass, dur in segments if symbol != "N"]
    return 0.0 if len(lengths) < 2 else statistics.stdev(lengths)


def normalize_output_stem(stem: str) -> str:
    if stem.endswith("_harmonized-optimizer"):
        return stem[:-len("_harmonized-optimizer")]
    if stem.endswith("_harmonized"):
        return stem[:-len("_harmonized")]
    return stem


def find_reference_file(generated_path: str) -> Optional[Path]:
    gen_path = Path(generated_path).resolve()
    ref_stem = normalize_output_stem(gen_path.stem)

    candidate_dirs = [
        gen_path.parent.parent / "MusicLibrary",
        Path(__file__).resolve().parent.parent / "MusicLibrary",
        Path.cwd() / "MusicLibrary",
        Path.cwd().parent / "MusicLibrary",
    ]

    for directory in candidate_dirs:
        if directory.exists():
            for ext in (".xml", ".musicxml"):
                candidate = directory / f"{ref_stem}{ext}"
                if candidate.exists():
                    return candidate
    return None


def normalize_kind(kind_raw: str, kind_text: str, symbol: str) -> str:
    raw = (kind_raw or "").strip().lower()
    text = (kind_text or "").strip().lower()
    sym = (symbol or "").strip().lower()
    combined = " ".join([raw, text, sym])

    if "suspended-second" in combined or "sus2" in combined:
        return "sus2"
    if "suspended-fourth" in combined or "sus4" in combined or re.search(r"\bsus\b", combined):
        return "sus4"
    if "major-ninth" in combined or "maj9" in combined:
        return "maj9"
    if "dominant-ninth" in combined or ("9" in combined and "maj9" not in combined and "m9" not in combined):
        return "9"
    if "minor-ninth" in combined or "min9" in combined or "mi9" in combined or "m9" in combined:
        return "m9"
    if "major-seventh" in combined or "maj7" in combined:
        return "maj7"
    if "minor-seventh" in combined or "min7" in combined or "mi7" in combined or "m7" in combined:
        return "m7"
    if "dominant-seventh" in combined or re.search(r"(?<!maj)(?<!m)7", combined):
        return "7"
    if "half-diminished" in combined or "m7b5" in combined:
        return "m7b5"
    if "diminished-seventh" in combined or "dim7" in combined:
        return "dim7"
    if "diminished" in combined or "dim" in combined:
        return "dim"
    if "augmented" in combined or "aug" in combined or "+" in combined:
        return "aug"
    if "minor-sixth" in combined or "m6" in combined or "min6" in combined:
        return "m6"
    if "major-sixth" in combined or re.search(r"(^|[^m])6", combined):
        return "6"
    if "minor" in raw or "minor" in text or "mi" in text or re.search(r"(^|[^a-z])m($|[^a-z])", sym):
        return "minor"
    if "power" in combined or raw == "5":
        return "5"
    return raw or text or "major"


def chord_pitch_classes(root: str, kind_raw: str, kind_text: str, symbol: str) -> Set[int]:
    root_pc = pitch_to_pc(root)
    if root_pc is None:
        return set()

    kind = normalize_kind(kind_raw, kind_text, symbol)
    intervals = {
        "major": [0, 4, 7],
        "minor": [0, 3, 7],
        "5": [0, 7],
        "dim": [0, 3, 6],
        "dim7": [0, 3, 6, 9],
        "m7b5": [0, 3, 6, 10],
        "aug": [0, 4, 8],
        "7": [0, 4, 7, 10],
        "maj7": [0, 4, 7, 11],
        "m7": [0, 3, 7, 10],
        "6": [0, 4, 7, 9],
        "m6": [0, 3, 7, 9],
        "9": [0, 4, 7, 10, 2],
        "maj9": [0, 4, 7, 11, 2],
        "m9": [0, 3, 7, 10, 2],
        "sus2": [0, 2, 7],
        "sus4": [0, 5, 7],
    }.get(kind, [0, 4, 7])

    return {(root_pc + x) % 12 for x in intervals}


def chord_function(root: str) -> str:
    pc = pitch_to_pc(root)
    if pc is None:
        return "O"
    if pc in {0, 9, 4}:   # C, A, E
        return "T"
    if pc in {5, 2}:      # F, D
        return "S"
    if pc in {7, 11, 1}:  # G, B, Db
        return "D"
    return "O"


def compute_exact_chord_match_ratio(gen_roots, gen_kinds_raw, gen_kinds_text, gen_symbols,
                                    ref_roots, ref_kinds_raw, ref_kinds_text, ref_symbols) -> float:
    n = min(len(gen_roots), len(ref_roots))
    if n == 0:
        return 0.0
    matches = 0
    for i in range(n):
        if gen_symbols[i] == "N" or ref_symbols[i] == "N":
            continue
        if gen_roots[i] == ref_roots[i] and \
           normalize_kind(gen_kinds_raw[i], gen_kinds_text[i], gen_symbols[i]) == \
           normalize_kind(ref_kinds_raw[i], ref_kinds_text[i], ref_symbols[i]):
            matches += 1
    return matches / n


def compute_functional_agreement_ratio(gen_roots, ref_roots) -> float:
    n = min(len(gen_roots), len(ref_roots))
    if n == 0:
        return 0.0
    matches = sum(1 for i in range(n) if chord_function(gen_roots[i]) == chord_function(ref_roots[i]))
    return matches / n


def compute_harmonic_similarity_ratio(gen_roots, gen_kinds_raw, gen_kinds_text, gen_symbols,
                                      ref_roots, ref_kinds_raw, ref_kinds_text, ref_symbols) -> float:
    n = min(len(gen_roots), len(ref_roots))
    if n == 0:
        return 0.0
    total = 0.0
    for i in range(n):
        gen_set = chord_pitch_classes(gen_roots[i], gen_kinds_raw[i], gen_kinds_text[i], gen_symbols[i])
        ref_set = chord_pitch_classes(ref_roots[i], ref_kinds_raw[i], ref_kinds_text[i], ref_symbols[i])
        if not gen_set or not ref_set:
            continue
        inter = len(gen_set & ref_set)
        union = len(gen_set | ref_set)
        total += (inter / union) if union else 0.0
    return total / n


def compute_final_function_match(gen_roots, ref_roots) -> float:
    if not gen_roots or not ref_roots:
        return 0.0
    return 1.0 if chord_function(gen_roots[-1]) == chord_function(ref_roots[-1]) else 0.0


def evaluate_file(path: str, debug: bool = False) -> EvaluationResult:
    root = parse_musicxml(path)
    part = get_first_part(root)
    beats_per_measure, beat_type = extract_score_structure(part)
    if beat_type != 4:
        raise RuntimeError(f"Unsupported beat-type {beat_type}. Current evaluator version expects quarter-note beats.")

    num_measures = count_measures(part)
    total_beats = num_measures * beats_per_measure

    events = extract_harmony_events(part, beats_per_measure, beat_type)
    beat_grid, bass_grid, root_grid, kind_raw_grid, kind_text_grid = expand_events_to_beat_grid(events, total_beats)
    segments = compress_segments_with_bass(beat_grid, bass_grid)
    num_segments = compute_num_harmonic_segments(segments)

    reference_file = ""
    reference_found = 0
    reference_num_harmony_events = 0
    reference_num_harmonic_segments = 0
    exact_chord_match_ratio = 0.0
    functional_agreement_ratio = 0.0
    harmonic_similarity_ratio = 0.0
    final_function_match = 0.0

    ref_path = find_reference_file(path)
    if ref_path is not None:
        reference_file = ref_path.name
        reference_found = 1

        ref_root = parse_musicxml(str(ref_path))
        ref_part = get_first_part(ref_root)
        ref_beats_per_measure, ref_beat_type = extract_score_structure(ref_part)
        if ref_beat_type == 4:
            ref_num_measures = count_measures(ref_part)
            ref_total_beats = ref_num_measures * ref_beats_per_measure
            ref_events = extract_harmony_events(ref_part, ref_beats_per_measure, ref_beat_type)
            ref_beat_grid, ref_bass_grid, ref_root_grid, ref_kind_raw_grid, ref_kind_text_grid = expand_events_to_beat_grid(
                ref_events, ref_total_beats
            )
            ref_segments = compress_segments_with_bass(ref_beat_grid, ref_bass_grid)

            reference_num_harmony_events = len(ref_events)
            reference_num_harmonic_segments = compute_num_harmonic_segments(ref_segments)

            exact_chord_match_ratio = compute_exact_chord_match_ratio(
                root_grid, kind_raw_grid, kind_text_grid, beat_grid,
                ref_root_grid, ref_kind_raw_grid, ref_kind_text_grid, ref_beat_grid
            )
            functional_agreement_ratio = compute_functional_agreement_ratio(root_grid, ref_root_grid)
            harmonic_similarity_ratio = compute_harmonic_similarity_ratio(
                root_grid, kind_raw_grid, kind_text_grid, beat_grid,
                ref_root_grid, ref_kind_raw_grid, ref_kind_text_grid, ref_beat_grid
            )
            final_function_match = compute_final_function_match(root_grid, ref_root_grid)

    if debug:
        print("\n--- DEBUG ---")
        print("Beat grid:", beat_grid[:64])
        print("Bass grid:", bass_grid[:64])
        print("Root grid:", root_grid[:64])
        print("Segments:", segments[:20])

    return EvaluationResult(
        file=Path(path).name,
        num_measures=num_measures,
        beats_per_measure=beats_per_measure,
        num_beats=total_beats,
        num_harmony_events=len(events),
        num_harmonic_segments=num_segments,
        chord_density_per_measure=round(compute_chord_density_per_measure(num_segments, num_measures), 4),
        avg_chord_duration_beats=round(compute_avg_chord_duration_beats(segments), 4),
        redundancy_ratio=round(compute_redundancy_ratio(total_beats, num_segments), 4),
        avg_bass_jump_semitones=round(compute_avg_bass_jump_semitones(segments), 4),
        segment_length_std=round(compute_segment_length_std(segments), 4),
        reference_file=reference_file,
        reference_found=reference_found,
        reference_num_harmony_events=reference_num_harmony_events,
        reference_num_harmonic_segments=reference_num_harmonic_segments,
        exact_chord_match_ratio=round(exact_chord_match_ratio, 4),
        functional_agreement_ratio=round(functional_agreement_ratio, 4),
        harmonic_similarity_ratio=round(harmonic_similarity_ratio, 4),
        final_function_match=round(final_function_match, 4),
    )


def write_csv(results: List[EvaluationResult], csv_path: str) -> None:
    if not results:
        return
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()))
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))


def print_result(result: EvaluationResult) -> None:
    print(f"\nFile: {result.file}")
    print(f"  Measures                    : {result.num_measures}")
    print(f"  Beats per measure           : {result.beats_per_measure}")
    print(f"  Total beats                 : {result.num_beats}")
    print(f"  Harmony events in XML       : {result.num_harmony_events}")
    print(f"  Harmonic segments           : {result.num_harmonic_segments}")
    print(f"  Chord density / measure     : {result.chord_density_per_measure}")
    print(f"  Avg chord duration (beats)  : {result.avg_chord_duration_beats}")
    print(f"  Redundancy ratio            : {result.redundancy_ratio}")
    print(f"  Avg bass jump (semitones)   : {result.avg_bass_jump_semitones}")
    print(f"  Segment length std          : {result.segment_length_std}")
    print(f"  Reference file              : {result.reference_file}")
    print(f"  Reference found             : {result.reference_found}")
    print(f"  Reference harmony events    : {result.reference_num_harmony_events}")
    print(f"  Reference harmonic segments : {result.reference_num_harmonic_segments}")
    print(f"  Exact chord match ratio     : {result.exact_chord_match_ratio}")
    print(f"  Functional agreement ratio  : {result.functional_agreement_ratio}")
    print(f"  Harmonic similarity ratio   : {result.harmonic_similarity_ratio}")
    print(f"  Final function match        : {result.final_function_match}")


def resolve_input_files(input_file: Optional[str], pattern: Optional[str]) -> List[str]:
    files: List[str] = []
    if input_file:
        files.append(input_file)
    if pattern:
        files.extend(sorted(glob.glob(pattern)))
    unique: List[str] = []
    seen = set()
    for f in files:
        if f not in seen:
            unique.append(f)
            seen.add(f)
    return unique


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AQH beat-level evaluator for MusicXML harmony.")
    parser.add_argument("--input", type=str, help="Path to one MusicXML file.")
    parser.add_argument("--glob", type=str, help='Glob pattern, e.g. "../advanced_quantum_harmonizer/output/*.musicxml"')
    parser.add_argument("--csv", type=str, help="Optional CSV output path.")
    parser.add_argument("--debug", action="store_true", help="Print parsed harmony events, beat grid, bass grid, and segments.")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    files = resolve_input_files(args.input, args.glob)
    if not files:
        raise SystemExit("No input files provided. Use --input or --glob.")

    results: List[EvaluationResult] = []
    for path in files:
        try:
            result = evaluate_file(path, debug=args.debug)
            results.append(result)
            print_result(result)
        except Exception as exc:
            print(f"\nERROR in file '{path}': {exc}")

    if args.csv and results:
        write_csv(results, args.csv)
        print(f"\nCSV saved to: {args.csv}")


if __name__ == "__main__":
    main()
