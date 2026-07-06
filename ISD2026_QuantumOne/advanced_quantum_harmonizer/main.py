# main.py
import subprocess
import sys

from dataclasses import dataclass
from pathlib import Path
from typing import List

from .config import OptimizerConfig
from .beat_representation import BeatEvent
from .musicxml_loader import musicxml_to_beats
from .transposition import detect_key_from_musicxml, compute_transposition_interval, transpose_events_to_c
from .quantum_block_solver import QuantumBlockResult, solve_block_beam_search, solve_block_quantum_inspired
from .overlap_merger import merge_block_results
from .chord_library import build_chord_pool
from .postprocessor import postprocess_harmony
from .exporter import write_musicxml_preserve_melody

@dataclass
class BeatBlock:
    block_index: int
    start_beat: int
    end_beat: int
    events: List[BeatEvent]

    @property
    def length(self) -> int:
        return len(self.events)


def build_overlapping_blocks(
    events: List[BeatEvent],
    block_size: int = 8,
    overlap: int = 2,
) -> List[BeatBlock]:
    if block_size <= 0:
        raise ValueError("block_size must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= block_size:
        raise ValueError("overlap must be smaller than block_size")

    step = block_size - overlap
    blocks: List[BeatBlock] = []

    start = 0
    block_idx = 0

    while start < len(events):
        end = min(start + block_size, len(events))
        chunk = events[start:end]

        if not chunk:
            break

        blocks.append(
            BeatBlock(
                block_index=block_idx,
                start_beat=chunk[0].global_beat_index,
                end_beat=chunk[-1].global_beat_index,
                events=chunk,
            )
        )

        if end == len(events):
            break

        start += step
        block_idx += 1

    return blocks


def prepare_input(xml_path: str, cfg: OptimizerConfig):
    events = musicxml_to_beats(xml_path)

    detected_key = detect_key_from_musicxml(xml_path)

    if cfg.transpose_to_c:
        semitone_shift_to_c = compute_transposition_interval(detected_key, "C")
        events = transpose_events_to_c(events, detected_key)
    else:
        semitone_shift_to_c = 0

    return events, detected_key, semitone_shift_to_c


def debug_print_blocks(blocks: List[BeatBlock]) -> None:
    print("\n=== BLOCKS ===")
    for block in blocks:
        print(
            f"Block {block.block_index:02d}: "
            f"beats {block.start_beat}-{block.end_beat} "
            f"(len={block.length})"
        )

def debug_print_events(events, limit=20):
    print("\n=== FIRST EVENTS ===")
    for ev in events[:limit]:
        print(
            f"beat={ev.global_beat_index}, "
            f"bar={ev.bar_index+1}, "
            f"beat_in_bar={ev.beat_in_bar+1}, "
            f"notes={ev.notes_midi}, "
            f"meter={ev.meter}"
        )

def solve_all_blocks(
    blocks: List[BeatBlock],
    chord_pool,
    cfg: OptimizerConfig,
) -> List[QuantumBlockResult]:
    results = []

    for i, block in enumerate(blocks):
        result = solve_block_quantum_inspired(
            block_events=block.events,
            chord_pool=chord_pool,
            cfg=cfg,
            block_index=block.block_index,
            candidate_count=8,
            iterations=24,
            samples_per_iteration=160,
            learning_rate=0.10,
            temperature=1.25,
            elite_fraction=0.25,
            coupling_strength=1.4,
            coupling_learning_rate=0.22,
            random_seed=None,
            is_first_block=(i == 0),
            is_last_block=(i == len(blocks) - 1),
        )
        results.append(result)

        print(f"\n[BLOCK {block.block_index:02d}] beats {result.start_beat}-{result.end_beat}")
        print("  Chords:", " | ".join(result.chords))
        print("  Score :", result.metadata.get("block_score"))

    return results

def find_harmonizer_optimizer_script(base_dir: Path) -> Path:
    """
    Expected location:
    one level above this project -> Harmonizer/musicxml_optimizer.py
    """
    candidate = base_dir.parent / "Harmonizer" / "musicxml_optimizer.py"

    if not candidate.exists():
        raise FileNotFoundError(
            f"Optimizer script not found: {candidate}"
        )

    return candidate


def run_external_optimizer(
    input_musicxml: Path,
    output_musicxml: Path,
    base_dir: Path,
    seed: int = 7,
    cadence: str = "Cmaj7",
    use_cadence: bool = True,
    use_inversions: bool = True,
    p2_oct: int = 3,
    p2_min_bass: int = 43,
    p2_max_top: int = 64,
) -> None:
    optimizer_script = find_harmonizer_optimizer_script(base_dir)

    cmd = [
        sys.executable,
        str(optimizer_script),
        "--in", str(input_musicxml),
        "--out", str(output_musicxml),
        "--seed", str(seed),
        "--cadence", cadence,
        "--p2-oct", str(p2_oct),
        "--p2-min-bass", str(p2_min_bass),
        "--p2-max-top", str(p2_max_top),
    ]

    if not use_cadence:
        cmd.append("--no-cadence")

    if not use_inversions:
        cmd.append("--no-inv")

    print("\\n=== RUN EXTERNAL HARMONIZER OPTIMIZER ===")
    print("Command:", " ".join(cmd))

    subprocess.run(cmd, check=True)

    print(f"Optimized MusicXML exported to: {output_musicxml}")

if __name__ == "__main__":
    cfg = OptimizerConfig()
    cfg.validate()

    # ---------------------------------------------------------
    # Paths
    # ---------------------------------------------------------
    BASE_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = BASE_DIR.parent

    INPUT_DIR = PROJECT_ROOT / "MusicLibrary"
    OUTPUT_DIR = BASE_DIR / "output"
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Change only this file name when testing different melodies 
    # // Folsom_Prison_Blues.musicxml
    # ---------------------------------------------------------
# BATCH MODE: process all files in MusicLibrary
# ---------------------------------------------------------

input_files = list(INPUT_DIR.glob("*.xml")) + list(INPUT_DIR.glob("*.musicxml"))

if not input_files:
    raise FileNotFoundError(f"No MusicXML files found in {INPUT_DIR}")

print(f"\n=== BATCH MODE ===")
print(f"Found {len(input_files)} input files.\n")

for xml_path in input_files:

    INPUT_FILE = xml_path.name
    print(f"\n==============================")
    print(f"Processing: {INPUT_FILE}")
    print(f"==============================")

    out_path = OUTPUT_DIR / f"{Path(INPUT_FILE).stem}_harmonized.musicxml"
    optimized_out_path = OUTPUT_DIR / f"{Path(INPUT_FILE).stem}_harmonized-optimizer.musicxml"

    # ---------------------------------------------------------
    # Load + preprocess
    # ---------------------------------------------------------
    events, detected_key, semitone_shift_to_c = prepare_input(str(xml_path), cfg)

    print(f"Detected key: {detected_key}")
    print(f"Semitone shift to C: {semitone_shift_to_c}")

    debug_print_events(events, limit=10)

    blocks = build_overlapping_blocks(
        events,
        block_size=cfg.block_size_beats,
        overlap=cfg.overlap_beats,
    )

    chord_pool = build_chord_pool(
        allow_triads=cfg.allow_triads,
        allow_sevenths=cfg.allow_seventh_chords,
        allow_secondary_dominants=cfg.allow_secondary_dominants,
    )

    print(f"\nLoaded {len(events)} beat events.")
    debug_print_blocks(blocks)

    # ---------------------------------------------------------
    # Solve blocks + merge
    # ---------------------------------------------------------
    block_results = solve_all_blocks(blocks, chord_pool, cfg)
    merged = merge_block_results(block_results, overlap=cfg.overlap_beats)

    print("\n=== MERGED RESULT ===")
    print("Raw chords:", " | ".join(merged.chords))

    # ---------------------------------------------------------
    # Postprocess
    # ---------------------------------------------------------
    final_chords = postprocess_harmony(
        chords=merged.chords,
        events=events,
        chord_pool=chord_pool,
        cfg=cfg,
    )

    print("\n=== POSTPROCESSED RESULT ===")
    print("Final chords:", " | ".join(final_chords))

    # ---------------------------------------------------------
    # Export RAW
    # ---------------------------------------------------------
    write_musicxml_preserve_melody(
        input_xml_path=str(xml_path),
        events=events,
        chords=final_chords,
        chord_pool=chord_pool,
        out_path=str(out_path),
        title=f"AQH - {Path(INPUT_FILE).stem}",
        composer="Josef P.",
        chord_base_octave=3,
        semitone_shift_to_c=semitone_shift_to_c,
    )

    print(f"\nRAW exported to: {out_path}")

    # ---------------------------------------------------------
    # Run optimizer
    # ---------------------------------------------------------
    run_external_optimizer(
        input_musicxml=out_path,
        output_musicxml=optimized_out_path,
        base_dir=BASE_DIR,
        seed=7,
        cadence="Cmaj7",
        use_cadence=True,
        use_inversions=True,
        p2_oct=3,
        p2_min_bass=43,
        p2_max_top=64,
    )