"""Select reproducible HookTheory TEST excerpts; no harmony passed to generator."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def eligible(record):
    a = record.get('annotations') or {}
    if record.get('split') != 'TEST':
        return False, 'not_test'
    if not {'MELODY', 'HARMONY'}.issubset(set(record.get('tags', []))):
        return False, 'missing_annotation_tag'
    if len(a.get('meters', [])) != 1 or len(a.get('keys', [])) != 1:
        return False, 'changing_or_missing_meter_key'
    meter = a['meters'][0]
    if (meter.get('beats_per_bar'), meter.get('beat_unit')) not in {(2,4),(3,4),(4,4),(6,8),(12,8)}:
        return False, 'unsupported_meter'
    if not a.get('melody') or not a.get('harmony'):
        return False, 'empty_melody_or_harmony'
    if not a.get('num_beats') or a['num_beats'] <= 0:
        return False, 'invalid_length'
    for event in a['melody']:
        if not all(k in event for k in ('onset','offset','pitch_class')) or event['offset'] <= event['onset']:
            return False, 'invalid_melody_event'
    return True, None


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True)
    p.add_argument('--output',default='results/hooktheory/selection.json')
    p.add_argument('--count',type=int,default=20)
    p.add_argument('--seed',default='EMH-HookTheory-AHFE-v1')
    args=p.parse_args()
    with gzip.open(args.input,'rt',encoding='utf-8') as f:
        dataset=json.load(f)
    candidates=[]; rejected={}
    for ident,rec in dataset.items():
        valid,reason=eligible(rec)
        if valid: candidates.append(ident)
        elif rec.get('split')=='TEST': rejected[reason]=rejected.get(reason,0)+1
    candidates.sort(key=lambda ident:(hashlib.sha256((args.seed+':'+ident).encode()).hexdigest(),ident))
    selected=candidates[:args.count]
    if len(selected)<args.count: raise RuntimeError('Not enough eligible records')
    out={'dataset':'SheetSage Hooktheory.json.gz','split':'TEST','seed':args.seed,'selection_method':'SHA256(seed + colon + record_id), ascending','requested':args.count,'eligible':len(candidates),'test_exclusion_counts':rejected,'selected':[]}
    for ident in selected:
        rec=dataset[ident];a=rec['annotations'];h=rec.get('hooktheory') or {}
        out['selected'].append({'id':ident,'artist':h.get('artist'),'song':h.get('song'),'meter':a['meters'][0],'num_beats':a['num_beats'],'melody_events':len(a['melody']),'reference_chords':len(a['harmony'])})
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f"Selected {len(selected)} TEST records from {len(candidates)} eligible; manifest: {dest}")

if __name__=='__main__':main()
