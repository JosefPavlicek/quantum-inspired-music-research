"""HookTheory scoring graph, using the frozen EMH engine in a separate process."""
import json
import sys
from fractions import Fraction
from pathlib import Path

# The parent experiment starts this worker with cwd=frozen EMH vendor.
# Keep the frozen EMH path intact; add original EMH only for its HookTheory
# loader/adapter. Never modify the original EMH project.
VENDOR = Path(__file__).resolve().parents[1] / "vendor" / "emh_baseline"
LEGACY_EMH = Path(__file__).resolve().parents[2] / "Explainable_Melody_Harmonizer"
sys.path.insert(0, str(LEGACY_EMH))
sys.path.insert(0, str(VENDOR))
from hooktheory.loader import load_dataset, melody_only, reference_only
from hooktheory.adapter import adapt
import importlib.util
bridge_path = Path(__file__).with_name("_emh_graph_worker.py")
spec = importlib.util.spec_from_file_location("harmonix_worker_bridge", bridge_path)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
bridge.VENDOR = VENDOR
from emh.key_detection import detect_key
from emh.harmony import generate_candidates
from emh.segmentation import segment_notes
from music21 import pitch
import yaml

def f(x):
    return Fraction(str(x)).limit_denominator(4096)

def reference_chord_for_segment(seg, harmony, candidates, bar):
    start = bar * (seg.measure - 1) + f(seg.start_beat) - 1
    end = start + f(seg.duration)
    overlaps = []
    for chord in harmony:
        w = max(Fraction(0), min(end, f(chord['offset'])) - max(start, f(chord['onset'])))
        if w:
            overlaps.append((w, chord))
    if not overlaps:
        return None, 'no_reference'
    # A segment containing multiple reference chords is not a clean single-label query.
    if len(overlaps) != 1 or overlaps[0][0] != end-start:
        return None, 'mixed_or_partial'
    ref = overlaps[0][1]
    root = int(ref['root_pitch_class']) % 12
    offsets = [0]
    for step in ref['root_position_intervals']:
        offsets.append((offsets[-1] + int(step)) % 12)
    pcs = frozenset((root+x)%12 for x in offsets)
    matching = [c.roman for c in candidates if _root(c.symbol) == root and c.pitch_classes == pcs]
    return (matching[0], 'covered') if len(matching)==1 else (None, 'out_of_vocabulary')

def _root(symbol):
    import re
    match = re.match(r'^([A-G](?:#|b|-)?)', symbol)
    return pitch.Pitch(match.group(1)).pitchClass if match else None

def main():
    archive, ident = sys.argv[1:3]
    dataset = load_dataset(archive)
    record = dataset[ident]
    melody = adapt(melody_only(record))
    # Generation sees melody ONLY; no reference passed to bridge.extract.
    bridge.load_musicxml = lambda _: melody
    graph = bridge.extract('unused')
    config = yaml.safe_load((VENDOR/'config.yaml').read_text(encoding='utf-8'))
    detected = detect_key(melody.notes)
    candidates = generate_candidates(detected.tonic, detected.mode, config)
    segments = segment_notes(melody.notes, melody.time_signatures, config)
    meter = record['annotations']['meters'][0]
    bar = Fraction(int(meter['beats_per_bar'])*4, int(meter['beat_unit']))
    reference = reference_only(record)
    labels = [reference_chord_for_segment(s,reference,candidates,bar) for s in segments]
    graph['reference'] = [x[0] for x in labels]
    graph['reference_status'] = [x[1] for x in labels]
    graph['id'] = ident
    graph['split'] = record.get('split')
    print(json.dumps(graph))

if __name__ == '__main__':
    main()
