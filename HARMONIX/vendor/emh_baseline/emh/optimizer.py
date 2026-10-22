"""Global Viterbi-like dynamic-programming optimizer for EMH."""
from dataclasses import dataclass
from emh.model import Decision, ScoreComponents
from emh.scoring import melody_compatibility,functional_transition,persistence,cadential_score,local_score,segment_has_sounding_notes

@dataclass
class Alternative:
    chord: object
    local_score: float
    path_score: float

_TIE_PRIORITY={"I":0,"V":1,"IV":2,"vi":3,"ii":4,"iii":5,"V7":6,"ii7":7,"vii°":8,"viiø7":9}
def _tie_rank(r): return _TIE_PRIORITY.get(r,100)
def _better(total,r,best,br,eps=1e-12):
    return best is None or total>best+eps or (abs(total-best)<=eps and _tie_rank(r)<_tie_rank(br))

def optimize(segments,candidates,key_pitch_classes,config=None):
    if not segments or not candidates:return []
    weights=(config or {}).get("scoring",{}).get("weights")
    dp=[];back=[];comps=[]
    for t,segment in enumerate(segments):
        row={};brow={};crow={};final=t==len(segments)-1
        rest_only=not segment_has_sounding_notes(segment)
        for chord in candidates:
            m=melody_compatibility(segment,chord,key_pitch_classes,config)
            if t==0:
                f=functional_transition(None,chord,config);p=persistence(None,chord,config);c=cadential_score(None,chord,final,config)
                loc=local_score(m,f,p,c,weights);row[chord.roman]=loc;brow[chord.roman]=None;crow[chord.roman]=(m,f,p,c,loc)
            else:
                bt=None;br=None;payload=None
                for prev in candidates:
                    # Scientific rule: silence alone cannot trigger a harmony change.
                    if rest_only and prev.roman!=chord.roman:
                        continue
                    f=functional_transition(prev,chord,config);p=persistence(prev,chord,config);c=cadential_score(prev,chord,final,config)
                    loc=local_score(m,f,p,c,weights);total=dp[t-1][prev.roman]+loc
                    if _better(total,prev.roman,bt,br):
                        bt,br,payload=total,prev.roman,(m,f,p,c,loc)
                if bt is not None:
                    row[chord.roman]=bt;brow[chord.roman]=br;crow[chord.roman]=payload
        dp.append(row);back.append(brow);comps.append(crow)
    last=None;best=None
    for rn,total in dp[-1].items():
        if _better(total,rn,best,last):best,last=total,rn
    path=[last]
    for t in range(len(segments)-1,0,-1):path.append(back[t][path[-1]])
    path.reverse()
    cmap={c.roman:c for c in candidates};decisions=[]
    alt_n=(config or {}).get("explainability",{}).get("alternatives",3)
    for t,rn in enumerate(path):
        m,f,p,c,loc=comps[t][rn];sc=ScoreComponents(m,f,p,c,loc,dp[t][rn])
        ordered=sorted(dp[t],key=lambda x:(-dp[t][x],_tie_rank(x)));alts=[]
        for ar in ordered:
            if ar==rn:continue
            am,af,ap,ac,aloc=comps[t][ar];alts.append(Alternative(cmap[ar],aloc,dp[t][ar]))
            if len(alts)>=alt_n:break
        decisions.append(Decision(segments[t],cmap[rn],sc,alts))
    return decisions
