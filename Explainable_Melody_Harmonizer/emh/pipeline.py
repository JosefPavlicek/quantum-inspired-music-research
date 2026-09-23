"""End-to-end EMH pipeline."""
from dataclasses import dataclass
from music21 import key as m21key
from emh.musicxml_loader import load_musicxml
from emh.segmentation import segment_notes
from emh.harmony import generate_candidates
from emh.optimizer import optimize
from emh.key_detection import detect_key, KeyDetectionResult

@dataclass(frozen=True)
class HarmonizationMetadata:
    xml_key: str | None
    detected_key: str
    key_detection_score: float
    key_source: str
    key_ranking: tuple

def _key_from_fifths(fifths):
    return m21key.KeySignature(fifths).asKey("major")

def _xml_key_name(fifths):
    if fifths is None:
        return None
    k=_key_from_fifths(fifths)
    return f"{k.tonic.name} major"

def harmonize_musicxml_with_metadata(path, config=None):
    melody=load_musicxml(path)
    detected: KeyDetectionResult=detect_key(melody.notes)
    key=m21key.Key(detected.tonic, detected.mode)
    segments=segment_notes(melody.notes,melody.time_signatures,config)
    candidates=generate_candidates(detected.tonic,detected.mode,config)
    scale={p.pitchClass for p in key.pitches}
    decisions=optimize(segments,candidates,scale,config)
    metadata=HarmonizationMetadata(
        xml_key=_xml_key_name(melody.key_signature_fifths),
        detected_key=detected.name,
        key_detection_score=detected.score,
        key_source="detected",
        key_ranking=detected.ranking,
    )
    return decisions, metadata

def harmonize_musicxml(path,config=None):
    """Backward-compatible API returning decisions only."""
    return harmonize_musicxml_with_metadata(path,config)[0]
