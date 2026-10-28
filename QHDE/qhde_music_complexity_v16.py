"""QHDE v0.16: conservative, QPU-free analysis of reference HookTheory harmony.
Run from repository root with HARMONIX environment. Only reads corpus/manifest.
Do not interpret 'score landscape' as whole-song musical complexity.
"""
from __future__ import annotations
import argparse, csv, gzip, hashlib, json, math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / 'HARMONIX/results/corpus_manifests/train_full.json'

def entropy(xs):
    if not xs: return None
    c=Counter(xs); n=len(xs)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

def stable_digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def inspect(value, level=0):
    """Schema preview only: never expose unneeded musical text or huge payloads."""
    if level >= 3: return type(value).__name__
    if isinstance(value,dict): return {k:inspect(v,level+1) for k,v in list(value.items())[:18]}
    if isinstance(value,list): return {'length':len(value),'first':inspect(value[0],level+1) if value else None}
    return type(value).__name__

def find_chord_collections(rec):
    """Find *only explicit* harmony/chord named containers; don't treat melody as chords."""
    found=[]
    def walk(node,path,depth):
        if depth > 6: return
        if isinstance(node,dict):
            for k,v in node.items():
                kp=str(k).lower(); next_path=path+[str(k)]
                if (kp in ('harmony','harmonies','chords','chord_annotations','chord_progression')
                        and isinstance(v,list) and v and all(isinstance(x,dict) for x in v[:3])):
                    found.append(('.'.join(next_path),v))
                if isinstance(v,(dict,list)): walk(v,next_path,depth+1)
        elif isinstance(node,list):
            # Walk only initial elements for schema-level discovery
            for i,v in enumerate(node[:2]):
                if isinstance(v,(dict,list)): walk(v,path+[str(i)],depth+1)
    walk(rec,[],0)
    return found

def chord_label(item):
    """Canonical pitch-class chord identity from the verified HookTheory schema.

    Root-position intervals represent successive intervals above the previous
    pitch; preserve the ordered interval signature and inversion separately.
    """
    root = item.get('root_pitch_class')
    intervals = item.get('root_position_intervals')
    inversion = item.get('inversion')
    onset = item.get('onset')
    offset = item.get('offset')
    if (type(root) is not int or not 0 <= root <= 11
            or not isinstance(intervals, list) or not intervals
            or any(type(v) is not int or not 0 < v <= 12 for v in intervals)
            or type(inversion) is not int or not 0 <= inversion <= len(intervals)
            or not isinstance(onset, (int, float)) or isinstance(onset, bool)
            or not isinstance(offset, (int, float)) or isinstance(offset, bool)
            or not onset < offset):
        return None
    return f"pc{root}:intervals({','.join(map(str, intervals))}):inv{inversion}"

def evaluate_record(rec):
    choices=[]
    for path,collection in find_chord_collections(rec):
        labels=[chord_label(x) for x in collection]
        good=[x for x in labels if x is not None]
        # Do not silently skip missing chord annotations: sequence would be invalid.
        choices.append((len(good),len(labels),path,labels))
    if not choices: return {'status':'unsupported_schema','reason':'No explicit chord/harmony list found','schema':inspect(rec)}
    valid=[x for x in choices if x[0] == x[1] and x[1] >= 2]
    if not valid:
        _,total,path,_=max(choices)
        return {'status':'incomplete_annotations','path':path,'items':total,'schema':inspect(rec)}
    # Favor longest complete explicit sequence; acknowledge ambiguous competing sequences.
    _,_,path,labels=max(valid,key=lambda x:x[1])
    transitions=list(zip(labels,labels[1:]))
    return {
      'status':'ok','chord_path':path,'n_chords':len(labels),
      'n_unique_chords':len(set(labels)),
      'unique_chord_ratio':len(set(labels))/len(labels),
      'chord_entropy_bits':entropy(labels),
      'transition_entropy_bits':entropy(transitions),
      'immediate_repetition_rate':sum(a==b for a,b in transitions)/len(transitions),
      'repeated_bigram_rate':1-len(set(transitions))/len(transitions),
      'n_distinct_transitions':len(set(transitions)),
      'warning':'Labels encode HookTheory root pitch class, ordered intervals and inversion. Key-aware function/chromaticity analysis is not validated; these are annotated clips, not necessarily whole songs.',
    }

def select_train(manifest,limit):
    if manifest.get('split')!='TRAIN' or manifest.get('preflight_only') is not True:
        raise ValueError('Expected audited TRAIN preflight manifest')
    ids=[x['id'] for x in manifest['selected']]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate IDs')
    return ids[:limit] if limit else ids

def run(archive,manifest,out,limit):
    from_path=Path(archive); manifest=Path(manifest); out=Path(out)
    ids=select_train(json.loads(manifest.read_text(encoding='utf-8')),limit)
    with gzip.open(from_path,'rt',encoding='utf-8') as f: dataset=json.load(f)
    rows=[]; diagnostics={}
    for ident in ids:
        if ident not in dataset:
            result={'status':'missing_record'}
        else:
            result=evaluate_record(dataset[ident])
        row={'record_id':ident, **{k:v for k,v in result.items() if k not in ('schema','warning')}}
        rows.append(row)
        if result['status']!='ok': diagnostics[ident]=result
    out.mkdir(parents=True,exist_ok=True)
    (out/'features.json').write_text(json.dumps({'version':'QHDE-v0.16','split':'TRAIN',
       'reference_harmony_used_for_analysis_only':True,'archive_name':from_path.name,
       'archive_sha256':stable_digest(from_path),'manifest_sha256':stable_digest(manifest),
       'rows':rows,'diagnostics':diagnostics},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    fields=['record_id','status','chord_path','n_chords','n_unique_chords','unique_chord_ratio',
      'chord_entropy_bits','transition_entropy_bits','immediate_repetition_rate',
      'repeated_bigram_rate','n_distinct_transitions','reason','path','items']
    with (out/'features.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    good=[r for r in rows if r['status']=='ok']
    report=[ '# QHDE v0.16 — independent music-descriptor audit','',
      f'Input TRAIN records: {len(rows)}; fully parsed chord sequences: {len(good)}.',
      'No quantum job submitted. No harmonization scoring used in descriptors.','',
      '## Scope and limitations','',
      '- Descriptors use source *reference harmony*, NOT corrected EMH candidate scores.',
      '- Chord identity combines root pitch class, ordered root-position intervals and inversion; not normalized for key or enharmonic notation.',
      '- No inference about whole-song complexity from QHDE two-segment optimization.',
      '- No blind prediction of ideal p is possible yet; next stage requires independent, held-out evaluation.',
      '- Unsupported schemas are reported rather than silently treated as valid chord sequences.',
      '', '## Parsed records (first 15)','',
      '| ID | Chords | Unique | Chord entropy (bits) | Transition entropy (bits) | Repeated bigrams |',
      '|---|---:|---:|---:|---:|---:|']
    for r in good[:15]:
        report.append(f"| {r['record_id']} | {r['n_chords']} | {r['n_unique_chords']} | {r['chord_entropy_bits']:.3f} | {r['transition_entropy_bits']:.3f} | {r['repeated_bigram_rate']:.2%} |")
    if diagnostics: report.extend(['','## Schema issues','', f'{len(diagnostics)} records could not be reliably interpreted. Inspect `features.json` diagnostics before publishing.'])
    (out/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(f'Processed {len(rows)} TRAIN records; valid explicit chord sequences {len(good)}; skipped {len(rows)-len(good)}')
    print('Saved',out/'features.csv',out/'features.json',out/'REPORT.md')
    print('OFFLINE ONLY — NO QPU SPEND')
    if not good: print('SCHEMA NEEDS REVIEW: share the diagnostics from features.json (without private data)')
    return len(good)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',default=str(DEFAULT_MANIFEST))
    p.add_argument('--archive',default=None)
    p.add_argument('--limit',type=int,default=100,help='TRAIN rows; 0 for all')
    p.add_argument('--out',default=str(ROOT/'QHDE/results/music_complexity_v16'))
    a=p.parse_args()
    if a.limit<0:p.error('--limit must be >=0')
    archive=a.archive
    if archive is None:
        import sys
        sys.path.insert(0,str(ROOT/'HARMONIX'))
        from harmonix.shared_data import require_hooktheory
        archive=require_hooktheory()
    run(archive,a.manifest,a.out,a.limit)
if __name__=='__main__': main()
