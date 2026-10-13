"""Post-hoc audit of iteration 3 outputs. No generation and no reference access during optimization."""
import argparse, collections, hashlib, json
from pathlib import Path

FIELDS=('root_agreement','chord_agreement','function_agreement','candidate_coverage','root_candidate_coverage','unmixed_root_agreement')

def audit(folder, core=None):
    folder=Path(folder)
    summary=json.loads((folder/'summary.json').read_text())
    ok=[r for r in summary if r['status']=='ok']
    exclusions=[r for r in summary if r['status']!='ok']
    counts=collections.Counter(); flags=collections.Counter(); examples={}
    per_case=[]; all_segments=[]
    for row in ok:
        detail=json.loads((folder/(row['id']+'.json')).read_text())
        segments=detail['evaluation']['segments']
        local=collections.Counter()
        for s in segments:
            counts['total']+=1
            if s['status']!='evaluated':
                counts['no_reference']+=1;local['no_reference']+=1;continue
            counts['evaluated']+=1;local['evaluated']+=1
            if s['mixed_reference']:flags['mixed_reference']+=1
            if s['reference_coverage_fraction'] < 0.999999:flags['partial_reference']+=1
            if s['dominant_reference_fraction'] < 0.5:flags['dominant_below_half']+=1
            if s['root_agreement']:flags['root_match']+=1
            if s['chord_agreement']:flags['chord_match']+=1
            if s['candidate_coverage']:flags['candidate_covered']+=1
            if s['root_candidate_coverage']:flags['root_covered']+=1
            if s['function_agreement'] is not None:
                flags['function_evaluable']+=1
                if s['function_agreement']:flags['function_match']+=1
            # Disjoint hierarchy: exact / unavailable / available-but-not-chosen.
            if s['chord_agreement']:
                category='exact_chord_match'
            elif not s['candidate_coverage']:
                category='reference_chord_unavailable'
            else:
                category='available_but_not_selected'
            counts[category]+=1;local[category]+=1
            # Flags are NOT causal explanations; they may overlap.
            if not s['root_candidate_coverage']:flags['root_unavailable']+=1
            if s['candidate_coverage'] and not s['root_agreement']:flags['covered_wrong_root']+=1
            if s['root_agreement'] and not s['chord_agreement']:flags['root_match_chord_mismatch']+=1
            if s['function_agreement'] is False:flags['function_mismatch']+=1
            if category not in examples:
                examples[category]={'case_id':row['id'],'segment':s['segment'],'generated_chord':s['generated_chord'],'human_root_pc':s['human_root_pc'],'human_pitch_classes':s['human_pitch_classes']}
            all_segments.append({'id':row['id'],'segment':s['segment'],'category':category,'mixed_reference':s['mixed_reference'],'partial_reference':s['reference_coverage_fraction']<0.999999,'function_agreement':s['function_agreement']})
        per_case.append({'id':row['id'],**dict(local)})
    n=counts['evaluated']
    assert counts['exact_chord_match']+counts['reference_chord_unavailable']+counts['available_but_not_selected']==n
    def pct(v,d=n):return round(100*v/d,2) if d else None
    output={'status':'post_hoc_diagnostics_only','cases':len(ok),'excluded':exclusions,'counts':dict(counts),'flags':dict(flags),
      'rates_pct':{'exact_chord_match':pct(counts['exact_chord_match']),'reference_chord_unavailable':pct(counts['reference_chord_unavailable']),
       'available_but_not_selected':pct(counts['available_but_not_selected']),'root_agreement':pct(flags['root_match']),
       'function_agreement':pct(flags['function_match'],flags['function_evaluable']),
       'chord_agreement_given_coverage':pct(counts['exact_chord_match'],counts['exact_chord_match']+counts['available_but_not_selected'])},
      'example_segments':examples,'per_case':per_case,
      'interpretation_limitations':['A dominant-overlap reference chord is a simplification, not a unique human solution.',
       'Function labels are inferred from EMH key and candidate roots, not independent human annotations.',
       'Mixed reference, key ambiguity, and temporal mismatch are diagnostic flags, not established causes.',
       'The 19-case selected sample supports descriptive PoC findings only.']}
    if core and Path(core).exists():
        files=sorted(Path(core).glob('*.py'))
        output['frozen_emh_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (folder/'diagnostics.json').write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n')
    lines=['# HookTheory × EMH v0.12 — frozen PoC audit','',f"Processed cases: **{len(ok)}**; evaluated segments: **{n}**; excluded: **{len(exclusions)}**.",'',
      '| Mutually exclusive segment outcome | Count | Percent |','|---|---:|---:|']
    for k,label in [('exact_chord_match','Exact chord match'),('reference_chord_unavailable','Human chord not in EMH candidate set'),('available_but_not_selected','Available but not selected')]:
        lines.append(f"| {label} | {counts[k]} | {pct(counts[k]):.2f}% |")
    lines+=['',f"Root agreement: **{flags['root_match']}/{n} ({pct(flags['root_match']):.2f}%)**.",
      f"Function agreement: **{flags['function_match']}/{flags['function_evaluable']} ({(str(pct(flags['function_match'],flags['function_evaluable'])) if flags['function_evaluable'] else 'N/A')}%)**.",
      f"Reference chord mixed within segment: **{flags['mixed_reference']}**; incomplete reference coverage: **{flags['partial_reference']}**.",
      '', '## Interpretation','',
      'These three categories distinguish representational limits from selection differences; they do not prove why an available chord was not selected.',
      'Human reference is assigned by maximum temporal overlap. Functional agreement uses EMH-derived tonal context and is not independent human-function ground truth.',
      'No EMH code or parameters were modified by this audit.','',
      '## Reproducibility','',
      '`python experiments/audit_hooktheory_poc.py --output results/hooktheory --core emh`','',
      'Generated: `diagnostics.json`, `diagnostics.md`.','']
    (folder/'diagnostics.md').write_text('\n'.join(lines))
    return output

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='results/hooktheory');p.add_argument('--core',default='emh')
    a=p.parse_args();r=audit(a.output,a.core)
    print(json.dumps({'cases':r['cases'],'evaluated':r['counts']['evaluated'],'rates_pct':r['rates_pct']},indent=2))
if __name__=='__main__':main()
