"""Run fixed EMH v0.12 on HookTheory TEST selection; post-hoc reference only."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from music21 import key as m21key
from emh.key_detection import detect_key
from emh.segmentation import segment_notes
from emh.harmony import generate_candidates
from emh.optimizer import optimize
from emh.explanation import decision_rows
from hooktheory.loader import load_dataset, melody_only, reference_only
from hooktheory.adapter import adapt
from hooktheory.evaluator import evaluate

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--dataset',default='data/hooktheory/Hooktheory.json.gz')
    ap.add_argument('--selection',default='selection.json')
    ap.add_argument('--output',default='results/hooktheory')
    args=ap.parse_args()
    dataset=load_dataset(args.dataset)
    selection=json.loads(Path(args.selection).read_text())
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    report=[]
    for item in selection['selected']:
        ident=item['id'];rec=dataset[ident]
        try:
            melody=adapt(melody_only(rec))
            detected=detect_key(melody.notes)
            segments=segment_notes(melody.notes,melody.time_signatures)
            candidates=generate_candidates(detected.tonic,detected.mode)
            scale={p.pitchClass for p in m21key.Key(detected.tonic,detected.mode).pitches}
            decisions=optimize(segments,candidates,scale)
            # Strictly AFTER optimization: access human reference annotations.
            evaluation=evaluate(decisions,reference_only(rec),rec['annotations']['meters'][0],candidates)
            (out/(ident+'.json')).write_text(json.dumps({'id':ident,'detected_key':detected.name,
                'decisions':decision_rows(decisions),'evaluation':evaluation},indent=2))
            report.append({'id':ident,'status':'ok',**evaluation['summary']})
        except Exception as ex:
            report.append({'id':ident,'status':'excluded','reason':str(ex)})
    (out/'summary.json').write_text(json.dumps(report,indent=2))
    valid=[r for r in report if r['status']=='ok']
    totals={}
    for field in ('root_agreement','chord_agreement','function_agreement','candidate_coverage','root_candidate_coverage','chord_agreement_given_coverage','unmixed_root_agreement'):
        # Different metrics have different denominators: compute from segment-level outputs.
        numer=denom=0
        for r in valid:
            detail=json.loads((out/(r['id']+'.json')).read_text())['evaluation']['segments']
            for s in detail:
                if s['status']!='evaluated':continue
                if field=='unmixed_root_agreement' and s['mixed_reference']:continue
                if field=='chord_agreement_given_coverage' and not s['candidate_coverage']:continue
                actual={'unmixed_root_agreement':'root_agreement','chord_agreement_given_coverage':'chord_agreement'}.get(field,field)
                if s[actual] is None:continue
                denom+=1;numer+=int(s[actual])
        totals[field]={'matches':numer,'evaluated':denom,'rate':numer/denom if denom else None}
    totals['processed_cases']=len(valid)
    totals['excluded_cases']=[{'id':r['id'],'reason':r['reason']} for r in report if r['status']!='ok']
    (out/'aggregate.json').write_text(json.dumps(totals,indent=2))
    print(json.dumps({'ok':sum(x['status']=='ok' for x in report),'excluded':sum(x['status']!='ok' for x in report),'summary':str(out/'summary.json')},indent=2))
if __name__=='__main__':main()
