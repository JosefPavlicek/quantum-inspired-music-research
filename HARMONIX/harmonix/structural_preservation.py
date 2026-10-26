"""Reference-blind structural query selection and post-hoc pattern preservation."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path
from statistics import mean
from .emh_bridge import EMHDecisionGraph, VENDOR
from .baseline import verify_snapshot
from .shared_data import require_hooktheory


def metrics(path, reference):
    """Observable chord and ordered-pattern metrics, only on known reference labels."""
    if len(path) != len(reference):
        raise ValueError('Misaligned paths')
    clean = [i for i, r in enumerate(reference) if r is not None]
    adjacent = [(i, i+1) for i in range(len(reference)-1)
                if reference[i] is not None and reference[i+1] is not None]
    repeated = [(i,j) for i in clean for j in clean if j > i and reference[i] == reference[j]]
    return {
        'exact_chord': mean(path[i] == reference[i] for i in clean) if clean else None,
        'exact_transition': mean((path[i],path[j]) == (reference[i],reference[j]) for i,j in adjacent) if adjacent else None,
        'reference_repetition_consistency': mean(path[i] == path[j] for i,j in repeated) if repeated else None,
        'n_clean':len(clean), 'n_adjacent':len(adjacent),'n_repeated_pairs':len(repeated),
    }


def evaluate(graph, reference):
    """All positions eligible for selection, including OOV/unknown/rest positions.

    Unanswerable query = no intervention. Random expectation enumerates ALL
    positions, not merely feasible or reference-covered positions.
    """
    baseline=graph.optimize()
    ranking=[p for p,_ in graph.rank_positions()]
    positions=list(range(len(graph.segments)))
    if sorted(ranking) != positions:
        raise ValueError('Ranking must cover every segment exactly once')
    base=metrics(baseline.choices,reference)
    def query(i):
        ref=reference[i]
        if ref is None or ref not in graph.chords:
            return baseline.choices, 'unanswerable'
        try:
            return graph.optimize({i:ref}).choices, 'answered'
        except ValueError:
            return baseline.choices, 'infeasible'
    per=[]
    for i in positions:
        choices,status=query(i)
        per.append({'position':i,'query_status':status,'metrics':metrics(choices,reference)})
    selected=per[ranking[0]]
    def compare(key):
        baseline_value=base[key]
        if baseline_value is None:
            return {'baseline':None,'targeted':None,'random_expected':None,'advantage':None}
        vals=[r['metrics'][key] for r in per]
        random=mean(vals)
        targeted=selected['metrics'][key]
        return {'baseline':baseline_value,'targeted':targeted,
                'random_expected':random,'advantage':targeted-random,
                'targeted_gain':targeted-baseline_value,'random_gain':random-baseline_value}
    return {
        'n_segments':len(positions),'selected_position':ranking[0],
        'selected_query_status':selected['query_status'],
        'n_answerable':sum(r['query_status']=='answered' for r in per),
        'reference_status_counts':{'covered':sum(r is not None for r in reference),
                                   'not_covered_or_unknown':sum(r is None for r in reference)},
        'comparisons':{k:compare(k) for k in ('exact_chord','exact_transition','reference_repetition_consistency')},
        'notes':'Reference-blind selection. Random expectation across ALL positions. Repetition consistency does not measure whether the repeated chord is correct.',
    }


def summarize(rows):
    good=[r for r in rows if r['status']=='ok']
    result={'n_requested':len(rows),'n_evaluated':len(good),'n_failed':len(rows)-len(good),
            'metrics':{},'warning':'Exploratory previously inspected TEST; song-level unweighted comparisons; not a confirmatory result.'}
    for key in ('exact_chord','exact_transition','reference_repetition_consistency'):
        values=[r['result']['comparisons'][key] for r in good if r['result']['comparisons'][key]['advantage'] is not None]
        result['metrics'][key]={'n_songs':len(values),
            'mean_advantage':mean(v['advantage'] for v in values) if values else None,
            'mean_targeted_gain':mean(v['targeted_gain'] for v in values) if values else None,
            'mean_random_gain':mean(v['random_gain'] for v in values) if values else None,
            'wins':sum(v['advantage']>1e-10 for v in values),
            'ties':sum(abs(v['advantage'])<=1e-10 for v in values),
            'losses':sum(v['advantage']< -1e-10 for v in values)}
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selection',required=True)
    p.add_argument('--output',default='results/structural_preservation_exploratory.json')
    p.add_argument('--limit',type=int,default=20)
    p.add_argument('--allow-exploratory-test',action='store_true')
    args=p.parse_args(argv)
    if args.limit<1: p.error('--limit must be >=1')
    manifest=json.loads(Path(args.selection).read_text(encoding='utf8'))
    split=manifest.get('split')
    if split=='TEST' and not args.allow_exploratory_test:
        p.error('Previously inspected TEST requires --allow-exploratory-test')
    if split not in ('TEST','DEV','TRAIN','VALIDATION'):
        p.error('Unknown split')
    verify_snapshot()
    archive=require_hooktheory()
    worker=Path(__file__).with_name('_hooktheory_worker.py')
    rows=[]
    for item in manifest['selected'][:args.limit]:
        ident=item['id']
        try:
            proc=subprocess.run([sys.executable,str(worker),str(archive),ident],cwd=VENDOR,
                                capture_output=True,text=True,check=True)
            data=json.loads(proc.stdout)
            if data.get('split')!=split: raise ValueError('Manifest/record split mismatch')
            graph=EMHDecisionGraph(data)
            if list(graph.optimize().choices)!=data['emh_baseline']:
                raise ValueError('Frozen EMH parity failure')
            result=evaluate(graph,data['reference'])
            rows.append({'id':ident,'status':'ok','result':result})
        except Exception as exc:
            rows.append({'id':ident,'status':'failed','reason':str(exc)[-800:]})
        print(ident,rows[-1]['status'],flush=True)
    report={'split':split,'exploratory':split=='TEST','summary':summarize(rows),'songs':rows}
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report['summary'],ensure_ascii=False,indent=2))
    if report['summary']['n_failed']: print('WARNING: inspect failed songs; no silent exclusions')

if __name__=='__main__': main()
