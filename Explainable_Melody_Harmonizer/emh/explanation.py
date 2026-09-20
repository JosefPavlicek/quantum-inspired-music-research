"""Decision-log export for EMH."""
import csv,json
from pathlib import Path

def decision_rows(decisions):
    rows=[]
    for d in decisions:
        rows.append({
            "segment":d.segment.index,"measure":d.segment.measure,
            "start_beat":str(d.segment.start_beat),"duration":str(d.segment.duration),
            "chord":d.selected.symbol,"roman":d.selected.roman,"function":d.selected.function,
            "melody_compatibility":d.scores.melody_compatibility,
            "functional_transition":d.scores.functional_transition,
            "persistence":d.scores.persistence,"cadence":d.scores.cadence,
            "local_score":d.scores.local_score,"path_score":d.scores.path_score,
            "alternatives":[{"chord":a.chord.symbol,"roman":a.chord.roman,
                             "local_score":a.local_score,"path_score":a.path_score}
                            for a in d.alternatives]
        })
    return rows

def export_json(decisions,path):
    Path(path).write_text(json.dumps(decision_rows(decisions),indent=2,ensure_ascii=False),encoding="utf-8")

def export_csv(decisions,path):
    rows=decision_rows(decisions)
    if not rows: return
    flat=[]
    for x in rows:
        y=dict(x); y["alternatives"]=json.dumps(y["alternatives"],ensure_ascii=False); flat.append(y)
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=flat[0].keys()); w.writeheader(); w.writerows(flat)
