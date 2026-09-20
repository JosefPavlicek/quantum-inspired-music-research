"""End-to-end EMH pipeline."""
from music21 import key as m21key
from emh.musicxml_loader import load_musicxml
from emh.segmentation import segment_notes
from emh.harmony import generate_candidates
from emh.optimizer import optimize

def _key_from_fifths(fifths):
    # V1: key signatures interpreted as major keys.
    return m21key.KeySignature(fifths).asKey("major")

def harmonize_musicxml(path,config=None):
    melody=load_musicxml(path)
    if melody.key_signature_fifths is None:
        raise ValueError("V1 requires a MusicXML key signature.")
    key=_key_from_fifths(melody.key_signature_fifths)
    segments=segment_notes(melody.notes,melody.time_signatures,config)
    candidates=generate_candidates(key.tonic.name,"major",config)
    scale={p.pitchClass for p in key.pitches}
    return optimize(segments,candidates,scale,config)
