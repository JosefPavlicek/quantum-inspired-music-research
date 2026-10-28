"""QHDE v0.17: independent, reproducible HookTheory clip selection; offline only.

Run from repository root. Reads HookTheory reference harmonies, never QAOA scores
for selection. Selected records are NOT yet executable QPU circuits.
"""
from __future__ import annotations
import argparse, csv, gzip, hashlib, json, math, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QHDE = Path(__file__).resolve().parent
sys.path.insert(0, str(QHDE))
from qhde_music_complexity_v16 import (DEFAULT_MANIFEST, chord_label,
    find_chord_collections, select_train, stable_digest)

PILOT_IDS = {'LAgQGkwEoyO','bWgMvrVkxlX','DpgvlyPBoad','nZgWXMVQxry','RPxeyBjaxb_'}

def shannon(labels):
    if not labels: return 0.0
    counts=Counter(labels); n=len(labels)
    return -sum((v/n)*math.log2(v/n) for v in counts.values())

def conditional_entropy(labels):
    """H(C[t+1] | C[t]) with per-predecessor empirical weighting."""
    if len(labels)<2: return 0.0
    successors=defaultdict(list)
    for a,b in zip(labels,labels[1:]): successors[a].append(b)
    return sum(len(v)/(len(labels)-1)*shannon(v) for v in successors.values())

def extract_labels(rec):
    complete=[]
    for path,items in find_chord_collections(rec):
        labels=[chord_label(item) for item in items]
        if len(labels)>=2 and all(x is not None for x in labels):
            # Temporal check: strictly time-ordered, non-overlap (gaps are allowed)
            onsets=[float(item['onset']) for item in items]
            offsets=[float(item['offset']) for item in items]
            if all(onsets[i]>=offsets[i-1] for i in range(1,len(items))):
                complete.append((len(labels),path,labels,items))
    if not complete: return None
    return max(complete,key=lambda x:x[0])

def analyze(rec, ident):
    ext=extract_labels(rec)
    if ext is None: return {'record_id':ident,'status':'invalid_or_overlapping'}
    _,path,labels,items=ext
    pairs=list(zip(labels,labels[1:]))
    counts=Counter(labels)
    n=len(labels)
    return {'record_id':ident,'status':'ok','chord_path':path,
       'n_chords':n,'n_unique_chords':len(counts),
       'unique_ratio':len(counts)/n,'chord_entropy_bits':shannon(labels),
       'conditional_transition_entropy_bits':conditional_entropy(labels),
       'repeated_bigram_rate':1-len(set(pairs))/len(pairs),
       'immediate_repetition_rate':sum(a==b for a,b in pairs)/len(pairs),
       'duration_beats':float(items[-1]['offset'])-float(items[0]['onset'])}

def quantile(values,q):
    values=sorted(values)
    if not values: return None
    x=(len(values)-1)*q; lo=int(x); hi=min(lo+1,len(values)-1)
    return values[lo]*(hi-x)+values[hi]*(x-lo)

def select(rows, per_group=4, minimum_chords=8, exclude_ids=frozenset()):
    """Music-only, deterministic stratified selection; no QAOA information."""
    eligible=[r for r in rows if r['status']=='ok' and r['n_chords']>=minimum_chords and r['record_id'] not in exclude_ids]
    if not eligible: raise ValueError('No valid eligible records; inspect manifest/filters')
    med_ent=quantile([r['conditional_transition_entropy_bits'] for r in eligible],.5)
    med_rep=quantile([r['repeated_bigram_rate'] for r in eligible],.5)
    groups=defaultdict(list)
    for r in eligible:
        e='high_entropy' if r['conditional_transition_entropy_bits']>med_ent else 'low_entropy'
        rep='high_repetition' if r['repeated_bigram_rate']>med_rep else 'low_repetition'
        groups[e+'__'+rep].append(r)
    selected=[]; counts={}
    for group in ['low_entropy__high_repetition','low_entropy__low_repetition',
                  'high_entropy__high_repetition','high_entropy__low_repetition']:
        rs=groups[group]
        # Selection within a stratum balances duration and is stable for fixed inputs.
        # Pick around median chord count to reduce size confounding, then hash tie-break.
        median_length=quantile([r['n_chords'] for r in rs],.5) if rs else 0
        rs=sorted(rs,key=lambda r:(abs(r['n_chords']-median_length),
                 hashlib.sha256(r['record_id'].encode()).hexdigest()))
        chosen=rs[:per_group]
        counts[group]={'eligible':len(rs),'selected':len(chosen)}
        for r in chosen: selected.append({**r,'stratum':group})
    return selected, {'median_conditional_entropy':med_ent,
      'median_repeated_bigram_rate':med_rep,'strata':counts,
      'eligible_count':len(eligible), 'selected_count':len(selected)}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive',default=None)
    ap.add_argument('--manifest',default=str(DEFAULT_MANIFEST))
    ap.add_argument('--limit',type=int,default=100,help='0 = all TRAIN records')
    ap.add_argument('--per-stratum',type=int,default=4)
    ap.add_argument('--min-chords',type=int,default=8)
    ap.add_argument('--exclude-pilot',action='store_true',default=True)
    ap.add_argument('--include-pilot',action='store_true')
    ap.add_argument('--out',default=str(ROOT/'QHDE/results/complexity_v17'))
    a=ap.parse_args()
    if a.limit<0 or a.per_stratum<1 or a.min_chords<2: ap.error('Invalid nonnegative limit or positive stratum/minimum values')
    manifest=Path(a.manifest)
    ids=select_train(json.loads(manifest.read_text(encoding='utf-8')),a.limit)
    if a.archive: archive=Path(a.archive)
    else:
        sys.path.insert(0,str(ROOT/'HARMONIX'))
        from harmonix.shared_data import require_hooktheory
        archive=Path(require_hooktheory())
    with gzip.open(archive,'rt',encoding='utf-8') as f: corpus=json.load(f)
    rows=[analyze(corpus[rid],rid) if rid in corpus else {'record_id':rid,'status':'missing'} for rid in ids]
    excluded=set() if a.include_pilot else PILOT_IDS
    chosen,metadata=select(rows, a.per_stratum,a.min_chords,excluded)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    payload={'version':'QHDE-v0.17','offline_only':True,'submitted_jobs':0,
        'split':'TRAIN','archive_sha256':stable_digest(archive),
        'manifest_sha256':stable_digest(manifest),
        'selection_only_reference_harmony':True,
        'pilot_records_excluded':not a.include_pilot,
        'no_qpu_circuits_prepared':True,'selected_ids':[r['record_id'] for r in chosen],
        'selection':metadata,'selected':chosen,'all_features':rows}
    (out/'selection.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    cols=['record_id','status','n_chords','n_unique_chords','unique_ratio','chord_entropy_bits',
        'conditional_transition_entropy_bits','repeated_bigram_rate','immediate_repetition_rate','duration_beats','stratum']
    for fname,items in [('features.csv',rows),('selected.csv',chosen)]:
        with (out/fname).open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(items)
    report=['# QHDE v0.17 — independent music-complexity selection','',
       f'Loaded {len(rows)} TRAIN clips; valid {sum(r["status"]=="ok" for r in rows)}; eligible {metadata["eligible_count"]}; selected {len(chosen)}.',
       '', '## Strata','', '| Stratum | Eligible | Selected |','|---|---:|---:|']
    for group,d in metadata['strata'].items(): report.append(f'| {group} | {d["eligible"]} | {d["selected"]} |')
    report+=['','## Selected clips','', '| ID | Chords | H(next chord given current) | Repeated bigrams | Stratum |','|---|---:|---:|---:|---|']
    for r in chosen: report.append(f'| {r["record_id"]} | {r["n_chords"]} | {r["conditional_transition_entropy_bits"]:.3f} | {r["repeated_bigram_rate"]:.1%} | {r["stratum"]} |')
    report+=['','## Study limits','',
       '- These are annotated HookTheory clips, not necessarily full compositions.',
       '- Music-only selection avoids selecting based on favorable QAOA outcomes.',
       '- Small samples and varying clip lengths/confounding remain. Strata can be sparse.',
       '- No corrected-EMH QAOA instance has been generated for new clips yet.',
       '- For each selected clip, generate a reference-blind score instance with the EXISTING corrected EMH bridge and an explicit fixed rule; do not assume v0.13 works on arbitrary clips.',
       '- Freeze the selection/parameters before new QPU evaluation; use held-out data for stronger claims.',
       '- No IBM API is called by this script.','']
    (out/'REPORT.md').write_text('\n'.join(report),encoding='utf-8')
    print(f'Processed {len(rows)} TRAIN clips; valid {sum(r["status"]=="ok" for r in rows)}; selected {len(chosen)}')
    for name,d in metadata['strata'].items():print(f'  {name}: {d["selected"]}/{d["eligible"]}')
    print('Saved',out/'selection.json',out/'selected.csv',out/'REPORT.md')
    print('OFFLINE ONLY — NO QPU JOBS SUBMITTED')

if __name__=='__main__': main()
