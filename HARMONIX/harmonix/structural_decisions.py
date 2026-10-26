"""Reference-blind global structural regularization on corrected EMH candidates.

A deterministic iterative Viterbi approximation, not a globally exact optimizer.
The structural model rewards same harmony for repeated melodic signatures,
and harmonic-function consistency for repeated melodic transitions.
"""
from collections import defaultdict
import sys
from pathlib import Path

# Import the frozen EMH scoring/optimizer implementation bundled with HARMONIX.
# Candidate generation remains the corrected HARMONIX implementation.
_VENDOR_EMH = Path(__file__).resolve().parents[1] / "vendor" / "emh_baseline"
if not (_VENDOR_EMH / "emh" / "scoring.py").is_file():
    raise ImportError(f"Frozen EMH dependency missing: {_VENDOR_EMH}")
if str(_VENDOR_EMH) not in sys.path:
    sys.path.insert(0, str(_VENDOR_EMH))

from emh.scoring import (melody_compatibility, functional_transition,
                         persistence, cadential_score, local_score,
                         segment_has_sounding_notes)


def signature(segment):
    """Relative pitch-class contour, duration-normalized; rests explicitly encoded."""
    sounding=[n for n in segment.notes if not n.is_rest and n.pitch_class is not None]
    if not sounding:return ('rest',)
    root=sounding[0].pitch_class
    return tuple((int(n.pitch_class-root)%12, round(float(n.duration/segment.duration),2))
                 for n in sounding)


def structural_links(segments):
    groups=defaultdict(list)
    for i,s in enumerate(segments):
        sig=signature(s)
        if sig!=('rest',):groups[sig].append(i)
    # Only links between nonadjacent occurrences, to avoid trivial persistence.
    links=[]
    for positions in groups.values():
        for a,b in zip(positions,positions[1:]):
            if b-a>1:links.append((a,b))
    return links


def optimize_structural(segments,candidates,scale,config=None, *,
                        repetition_weight=0.12, transition_weight=0.06,
                        iterations=4):
    """Returns (candidate path, explanation). No reference annotations are used.

    Structural rewards are a fixed-point approximation: each iteration runs
    an exact Viterbi step with link endpoints fixed to the previous path.
    Return the best *true* structural objective among visited paths.
    """
    if not segments or not candidates:return [],{'links':[],'iterations':0}
    if min(repetition_weight,transition_weight)<0 or iterations<1:
        raise ValueError('Nonnegative weights and >=1 iteration required')
    from emh.optimizer import optimize as baseline_optimize
    initial=baseline_optimize(segments,candidates,scale,config)
    links=structural_links(segments)
    cmap={c.roman:c for c in candidates}
    start=[d.selected.roman for d in initial]
    weights=(config or {}).get('scoring',{}).get('weights')
    n=len(segments)
    mvals=[[melody_compatibility(s,c,scale,config) for c in candidates] for s in segments]
    cidx={c.roman:i for i,c in enumerate(candidates)}
    neighbors=[[] for _ in segments]
    for a,b in links:neighbors[a].append(b);neighbors[b].append(a)
    # Pairwise link reward in the true objective, counted once per link.
    def objective(path):
        score=0.
        for t,r in enumerate(path):
            c=cmap[r];prev=cmap[path[t-1]] if t else None
            score+=local_score(mvals[t][cidx[r]],functional_transition(prev,c,config),
                               persistence(prev,c,config),cadential_score(prev,c,t==n-1,config),weights)
        for a,b in links:
            ca,cb=cmap[path[a]],cmap[path[b]]
            score+=repetition_weight*(ca.roman==cb.roman)
            if a and b:
                score+=transition_weight*(cmap[path[a-1]].function==cmap[path[b-1]].function and ca.function==cb.function)
        return score
    best=start;best_score=objective(start);current=start
    for _ in range(iterations):
        dp=[];backs=[]
        for t,s in enumerate(segments):
            row={};back={}
            for j,c in enumerate(candidates):
                bonus=repetition_weight*sum(c.roman==current[k] for k in neighbors[t])
                # Function-transition link approximated against fixed previous path.
                if t:
                    for a,b in links:
                        if t==a and a and b:
                            bonus+=transition_weight*(c.function==cmap[current[b]].function and cmap[current[a-1]].function==cmap[current[b-1]].function)
                        elif t==b and a:
                            bonus+=transition_weight*(c.function==cmap[current[a]].function and cmap[current[b-1]].function==cmap[current[a-1]].function)
                choices=[None] if t==0 else candidates
                for prev in choices:
                    if t and not segment_has_sounding_notes(s) and prev.roman!=c.roman:continue
                    prior=0 if prev is None else dp[t-1].get(prev.roman,float('-inf'))
                    val=prior+local_score(mvals[t][j],functional_transition(prev,c,config),
                              persistence(prev,c,config),cadential_score(prev,c,t==n-1,config),weights)+bonus
                    if c.roman not in row or val>row[c.roman]+1e-12:
                        row[c.roman]=val;back[c.roman]=None if prev is None else prev.roman
            if not row:raise ValueError('No feasible structural path')
            dp.append(row);backs.append(back)
        last=max(dp[-1],key=dp[-1].get);path=[last]
        for t in range(n-1,0,-1):path.append(backs[t][path[-1]])
        path.reverse()
        score=objective(path)
        if score>best_score+1e-12:best,best_score=path,score
        if path==current:break
        current=path
    return [cmap[r] for r in best],{'links':links,'iterations':iterations,
       'objective':best_score,'baseline_objective':objective(start),
       'repetition_weight':repetition_weight,'transition_weight':transition_weight,
       'method':'iterative_viterbi_approximation'}
