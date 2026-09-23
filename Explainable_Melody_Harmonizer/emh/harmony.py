"""Explainable diatonic chord candidate generation."""
from music21 import key as m21key
from emh.model import ChordCandidate

_FUNCTIONS_MAJOR = {1:"tonic",2:"predominant",3:"tonic",4:"predominant",5:"dominant",6:"tonic",7:"dominant"}
_FUNCTIONS_MINOR = {1:"tonic",2:"predominant",3:"tonic",4:"predominant",5:"dominant",6:"tonic",7:"dominant"}

def _roman_for_degree(degree, quality, seventh=False, mode="major"):
    nums={1:"I",2:"II",3:"III",4:"IV",5:"V",6:"VI",7:"VII"}
    rn=nums[degree]
    if quality in {"minor","diminished"}: rn=rn.lower()
    if quality=="diminished": rn += "°"
    if seventh:
        if quality=="diminished": rn=rn[:-1]+"ø7"
        else: rn += "7"
    return rn

def _symbol(root, quality, seventh=False):
    s=root
    if quality=="minor": s+="m"
    elif quality=="diminished": s+="dim"
    if seventh: s+="7"
    return s

def _pcs(root_pc, intervals):
    return frozenset((root_pc+i) % 12 for i in intervals)

def generate_candidates(tonic, mode="major", config=None):
    """Generate transparent diatonic candidates for major or natural minor."""
    if mode not in {"major", "minor"}:
        raise ValueError(f"Unsupported mode: {mode}")
    k=m21key.Key(tonic, mode)
    out=[]
    if mode == "major":
        qualities=["major","minor","minor","major","major","minor","diminished"]
        functions=_FUNCTIONS_MAJOR
    else:
        # Natural-minor diatonic baseline. Chromatic raised-leading-tone harmony
        # remains outside this baseline and can be added as an explicit extension.
        qualities=["minor","diminished","major","minor","minor","major","major"]
        functions=_FUNCTIONS_MINOR
    triads={"major":(0,4,7),"minor":(0,3,7),"diminished":(0,3,6)}
    for degree,quality in enumerate(qualities,1):
        root_pitch=k.pitchFromDegree(degree)
        out.append(ChordCandidate(_symbol(root_pitch.name,quality),_roman_for_degree(degree,quality,mode=mode),_pcs(root_pitch.pitchClass,triads[quality]),functions[degree]))
    # Same structural extension as V1: degree ii, V, vii seventh variants.
    for degree in (2,5,7):
        quality=qualities[degree-1]
        root_pitch=k.pitchFromDegree(degree)
        intervals={"major":(0,4,7,11),"minor":(0,3,7,10),"diminished":(0,3,6,10)}[quality]
        out.append(ChordCandidate(_symbol(root_pitch.name,quality,True),_roman_for_degree(degree,quality,True,mode),_pcs(root_pitch.pitchClass,intervals),functions[degree]))
    return out
