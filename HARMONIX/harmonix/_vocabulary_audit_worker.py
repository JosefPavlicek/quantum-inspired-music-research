"""Isolated HookTheory/EMH audit worker. Read-only original EMH and frozen vendor."""
import importlib.util
import json
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENDOR = Path(__file__).resolve().parents[1] / 'vendor' / 'emh_baseline'
sys.path.insert(0, str(ROOT / 'Explainable_Melody_Harmonizer'))
sys.path.insert(0, str(VENDOR))
from hooktheory.loader import load_dataset, melody_only, reference_only
from hooktheory.adapter import adapt
from emh.key_detection import detect_key
from emh.harmony import generate_candidates
from emh.segmentation import segment_notes
from music21 import pitch
import yaml

spec = importlib.util.spec_from_file_location('hooktheory_worker_for_audit', Path(__file__).with_name('_hooktheory_worker.py'))
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
spec2 = importlib.util.spec_from_file_location('vocabulary_audit_module', Path(__file__).with_name('vocabulary_audit.py'))
# Avoid importing package modules in worker: classification is replicated via a small pure helper.

def fraction(value):
    return Fraction(str(value)).limit_denominator(4096)

def main():
    archive, ident = sys.argv[1:3]
    record = load_dataset(archive)[ident]
    melody = adapt(melody_only(record))
    config = yaml.safe_load((VENDOR/'config.yaml').read_text(encoding='utf8'))
    detected = detect_key(melody.notes)
    candidates = generate_candidates(detected.tonic, detected.mode, config)
    segments = segment_notes(melody.notes, melody.time_signatures, config)
    meter = record['annotations']['meters'][0]
    bar = Fraction(int(meter['beats_per_bar'])*4, int(meter['beat_unit']))
    harmony = reference_only(record)
    result=[]
    for i, seg in enumerate(segments):
        start = bar * (seg.measure - 1) + fraction(seg.start_beat) - 1
        end = start + fraction(seg.duration)
        overlaps=[]
        for chord in harmony:
            w=max(Fraction(0),min(end,fraction(chord['offset']))-max(start,fraction(chord['onset'])))
            if w:
                overlaps.append((w,chord))
        row={'id':ident,'segment_index':i,'measure':seg.measure,'start_beat':str(seg.start_beat),
             'status':'no_reference','quality':None,'root_pitch_class':None,'intervals':None,
             'relative_pitch_classes':None,'root_match_any':False,'pitch_class_match_any':False,
             'candidate_count':len(candidates)}
        if not overlaps:
            result.append(row);continue
        if len(overlaps)!=1 or overlaps[0][0]!=end-start:
            row['status']='mixed_or_partial';result.append(row);continue
        chord=overlaps[0][1]
        root=int(chord['root_pitch_class'])%12
        intervals=list(chord['root_position_intervals'])
        offsets={0};cur=0
        for step in intervals:
            cur=(cur+int(step))%12;offsets.add(cur)
        absolute=frozenset((root+pc)%12 for pc in offsets)
        matching=[c for c in candidates if worker._root(c.symbol)==root and c.pitch_classes==absolute]
        row.update({'root_pitch_class':root,'intervals':intervals,
                    'relative_pitch_classes':sorted(offsets),
                    'root_match_any':any(worker._root(c.symbol)==root for c in candidates),
                    'pitch_class_match_any':any(c.pitch_classes==absolute for c in candidates),
                    'status':'covered' if len(matching)==1 else 'out_of_vocabulary'})
        # Classification is strictly descriptive; derived from pitch-class set.
        signatures={
            (0,4,7):'major_triad',(0,3,7):'minor_triad',(0,3,6):'diminished_triad',
            (0,4,8):'augmented_triad',(0,2,7):'sus2',(0,5,7):'sus4',
            (0,4,7,9):'major_sixth',(0,3,7,9):'minor_sixth',
            (0,4,7,10):'dominant_seventh',(0,4,7,11):'major_seventh',
            (0,3,7,10):'minor_seventh',(0,3,6,10):'half_diminished_seventh',
            (0,3,6,9):'diminished_seventh',(0,3,7,11):'minor_major_seventh',
        }
        # Keys are pitch-class sorted, not interval order.
        sig={tuple(sorted(k)):v for k,v in signatures.items()}
        row['quality']=sig.get(tuple(sorted(offsets)),
             'extended_or_complex' if len(offsets)>=5 else
             'other_four_note' if len(offsets)==4 else
             'other_triad' if len(offsets)==3 else 'other_or_incomplete')
        result.append(row)
    print(json.dumps({'id':ident,'audit_rows':result},ensure_ascii=False))

if __name__=='__main__':
    main()
