"""Corpus experiment: reference-blind query location, reference-based oracle response."""
import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from statistics import mean
from .emh_bridge import EMHDecisionGraph, VENDOR
from .baseline import verify_snapshot
from .shared_data import require_hooktheory


def evaluate_graph(graph, reference):
    if len(reference) != len(graph.segments):
        raise ValueError('Unaligned reference')
    baseline = graph.optimize()
    eligible = [i for i, c in enumerate(reference) if c in graph.chords]
    if not eligible:
        raise ValueError('No fully aligned, vocabulary-covered reference chords')
    def agreement(choices):
        return sum(choices[i] == reference[i] for i in eligible) / len(eligible)
    before = agreement(baseline.choices)
    # All position rankings are computed with NO reference information.
    ranking = [i for i, _ in graph.rank_positions()]
    # Only now reveal which positions have a feasible reference correction.
    candidates = {}
    for i in eligible:
        try:
            result = graph.optimize({i: reference[i]})
        except ValueError:
            continue
        candidates[i] = agreement(result.choices)
    chosen = next((i for i in ranking if i in candidates), None)
    if chosen is None:
        raise ValueError('No feasible oracle queries')
    return {
        'segments': len(reference), 'covered_segments': len(eligible),
        'baseline_agreement': before,
        'chosen_position': chosen, 'chosen_agreement': candidates[chosen],
        'chosen_gain': candidates[chosen]-before,
        'random_expected_agreement': mean(candidates.values()),
        'random_expected_gain': mean(candidates.values())-before,
        'advantage_over_random': candidates[chosen]-mean(candidates.values()),
        'candidate_count': len(candidates),
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--selection', required=True, help='Original EMH selection.json, containing TEST IDs')
    ap.add_argument('--output', default='results/hooktheory_oracle.json')
    ap.add_argument('--limit', type=int, default=20)
    args=ap.parse_args()
    verify_snapshot()
    archive=require_hooktheory()
    selection=json.loads(Path(args.selection).read_text(encoding='utf-8'))
    if selection.get('split') != 'TEST':
        raise ValueError('Only preregistered TEST selection is supported')
    rows=[]
    worker=Path(__file__).with_name('_hooktheory_worker.py')
    bridge=Path(__file__).with_name('_emh_graph_worker.py')
    for item in selection['selected'][:args.limit]:
        ident=item['id']
        try:
            proc=subprocess.run([sys.executable,str(worker),str(archive),ident], cwd=VENDOR,
                                capture_output=True,text=True,check=True)
            data=json.loads(proc.stdout)
            graph=EMHDecisionGraph(data)
            if list(graph.optimize().choices)!=data['emh_baseline']:
                raise ValueError('Frozen EMH parity failure')
            result=evaluate_graph(graph,data['reference'])
            rows.append({'id':ident,'status':'ok','reference_status_counts':dict(Counter(data['reference_status'])),**result})
        except Exception as exc:
            rows.append({'id':ident,'status':'excluded','reason':str(exc)[-600:]})
        print(f'{ident}: {rows[-1]["status"]}',flush=True)
    good=[r for r in rows if r['status']=='ok']
    summary={'n_selected':len(rows),'n_evaluated':len(good),'n_excluded':len(rows)-len(good),
             'mean_baseline_agreement':mean(r['baseline_agreement'] for r in good) if good else None,
             'mean_targeted_gain':mean(r['chosen_gain'] for r in good) if good else None,
             'mean_random_expected_gain':mean(r['random_expected_gain'] for r in good) if good else None,
             'mean_targeted_advantage':mean(r['advantage_over_random'] for r in good) if good else None,
             'wins_ties_losses':{'wins':sum(r['advantage_over_random']>1e-10 for r in good),
                                  'ties':sum(abs(r['advantage_over_random'])<=1e-10 for r in good),
                                  'losses':sum(r['advantage_over_random']< -1e-10 for r in good)},
             'warning':'Exploratory study; only exact reference chords in EMH vocabulary; missing/mixed labels excluded. Selection may be biased by feasibility filtering. Not musical quality.'}
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'summary':summary,'songs':rows},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))
    print('Report:',output)

if __name__=='__main__':main()
