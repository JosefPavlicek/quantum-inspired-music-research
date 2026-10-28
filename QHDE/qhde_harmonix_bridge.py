"""QHDE v0.3: export exact two-position scores from HARMONIX corrected candidates.

Read-only with respect to HARMONIX. No IBM hardware calls.
Use inside repository with HARMONIX package on Python path.
"""
from __future__ import annotations
import json
import math
from pathlib import Path


def pair_scores(segments, tonic, mode, scale, config, *, scoring=None, candidate_builder=None):
    """Return all (corrected candidate A, corrected candidate B) scores.

    Segments: exactly two preprocessed EMH segments.
    scoring: optional dictionary of original EMH scoring functions (for tests).
    candidate_builder: optional builder of EMH ChordCandidate objects (for tests).
    """
    if len(segments) != 2:
        raise ValueError('Exactly two consecutive segments required')
    if scoring is None:
        from emh.scoring import (melody_compatibility, functional_transition,
                                 persistence, cadential_score, local_score,
                                 segment_has_sounding_notes)
        scoring = dict(melody_compatibility=melody_compatibility,
                       functional_transition=functional_transition,
                       persistence=persistence, cadential_score=cadential_score,
                       local_score=local_score,
                       segment_has_sounding_notes=segment_has_sounding_notes)
    from harmonix.knowledge_candidates import generate
    knowledge = generate(tonic, mode, 'corrected')
    if candidate_builder is None:
        from emh.model import ChordCandidate
        candidate_builder = ChordCandidate
    candidates = [candidate_builder(c.symbol,c.roman,c.pitch_classes,c.function)
                  for c in knowledge]
    if not candidates:
        raise ValueError('No corrected candidates')
    if len({c.roman for c in candidates}) != len(candidates):
        raise ValueError('Ambiguous roman keys in candidate vocabulary')
    weights = (config or {}).get('scoring',{}).get('weights')
    mel = scoring['melody_compatibility']
    transition = scoring['functional_transition']
    persistence = scoring['persistence']
    cadence = scoring['cadential_score']
    local = scoring['local_score']
    sound = scoring['segment_has_sounding_notes']
    # For a two-position excerpt, the second position is considered final.
    # This is a *local two-segment task*, not necessarily a full-song score.
    rows=[]
    for i,a in enumerate(candidates):
        m0=mel(segments[0],a,scale,config)
        first=local(m0,transition(None,a,config),persistence(None,a,config),
                    cadence(None,a,False,config),weights)
        for j,b in enumerate(candidates):
            if not sound(segments[1]) and a.roman != b.roman:
                continue
            m1=mel(segments[1],b,scale,config)
            second=local(m1,transition(a,b,config),persistence(a,b,config),
                         cadence(a,b,True,config),weights)
            rows.append({'a':a.symbol,'a_roman':a.roman,'b':b.symbol,
                         'b_roman':b.roman,'a_index':i,'b_index':j,
                         'score':float(first+second)})
    rows.sort(key=lambda r:(r['a_index'],r['b_index']))
    if not rows or not all(math.isfinite(row['score']) for row in rows):
        raise ValueError('Empty or nonfinite scoring output')
    return {'model':'harmonix_corrected_candidates_frozen_emh_scoring',
            'candidate_variant':'corrected','tonic':tonic,'mode':mode,
            'candidate_count':len(candidates), 'pair_count':len(rows),
            'segments':2,'second_segment_is_final':True,
            'candidate_vocabulary':[{'symbol':c.symbol,'roman':c.roman,
                                     'function':c.function,
                                     'pitch_classes':sorted(c.pitch_classes)} for c in knowledge],
            'pairs':rows}


def save_scores(path, result):
    p=Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return p
