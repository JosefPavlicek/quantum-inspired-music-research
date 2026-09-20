"""Transparent scoring components for EMH."""
from fractions import Fraction

DEFAULT_WEIGHTS={"melody_compatibility":0.50,"functional_transition":0.25,"persistence":0.10,"cadence":0.15}
TRANSITIONS={
 ("tonic","tonic"):0.65, ("tonic","predominant"):0.90, ("tonic","dominant"):0.80,
 ("predominant","tonic"):0.45, ("predominant","predominant"):0.55, ("predominant","dominant"):1.00,
 ("dominant","tonic"):1.00, ("dominant","predominant"):0.25, ("dominant","dominant"):0.55,
}

def segment_has_sounding_notes(segment):
    return any(not n.is_rest for n in segment.notes)

def _overlap(note, segment):
    if note.is_rest: return Fraction(0)
    local=note.beat-Fraction(1)
    seg_start=segment.start_beat-Fraction(1)
    seg_end=seg_start+segment.duration
    return max(Fraction(0), min(local+note.duration,seg_end)-max(local,seg_start))

def melody_compatibility(segment, chord, key_pitch_classes=None, config=None):
    num=0.0; den=0.0
    chord_value=1.0; scale_value=0.45; chromatic_value=0.0
    if config:
        m=config.get("scoring",{}).get("melody",{})
        chord_value=m.get("chord_tone",chord_value)
        scale_value=m.get("diatonic_non_chord_tone",scale_value)
        chromatic_value=m.get("chromatic_non_chord_tone",chromatic_value)
    for n in segment.notes:
        d=float(_overlap(n,segment))
        if d<=0: continue
        w=d*n.metric_strength; den+=w
        if n.pitch_class in chord.pitch_classes: q=chord_value
        elif key_pitch_classes is not None and n.pitch_class in key_pitch_classes: q=scale_value
        else: q=chromatic_value
        num+=w*q
    return num/den if den else 0.0

def functional_transition(previous_chord, chord, config=None):
    if previous_chord is None: return 0.5
    return TRANSITIONS[(previous_chord.function,chord.function)]

def persistence(previous_chord, chord, config=None):
    if previous_chord is None: return 0.5
    same=1.0; change=0.55
    if config:
        p=config.get("scoring",{}).get("persistence",{})
        same=p.get("same_chord",same); change=p.get("chord_change",change)
    return same if previous_chord.roman==chord.roman else change

def cadential_score(previous_chord, chord, is_final=False, config=None):
    if not is_final: return 0.0
    if previous_chord and previous_chord.function=="dominant" and chord.roman=="I": return 1.0
    if chord.roman=="I": return 0.75
    return 0.0

def local_score(melody, transition, persist, cadence, weights=None):
    w=weights or DEFAULT_WEIGHTS
    return (w["melody_compatibility"]*melody+w["functional_transition"]*transition+
            w["persistence"]*persist+w["cadence"]*cadence)
