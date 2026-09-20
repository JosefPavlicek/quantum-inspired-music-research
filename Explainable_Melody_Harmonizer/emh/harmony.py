"""Explainable diatonic chord candidate generation."""
from music21 import key as m21key
from emh.model import ChordCandidate

_FUNCTIONS = {
    1: "tonic", 2: "predominant", 3: "tonic",
    4: "predominant", 5: "dominant", 6: "tonic", 7: "dominant",
}

def _roman_for_degree(degree, quality, seventh=False):
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

def generate_candidates(tonic, mode="major", config=None):
    """Generate diatonic candidates. V1 currently supports major keys."""
    if mode != "major":
        raise NotImplementedError("Minor-key candidate generation is planned after V1 major-key validation.")
    k=m21key.Key(tonic, mode)
    out=[]
    # Major-scale triad qualities.
    qualities=["major","minor","minor","major","major","minor","diminished"]
    for degree,quality in enumerate(qualities,1):
        pitches=[k.pitchFromDegree(degree+i*2).pitchClass for i in range(3)]
        root=k.pitchFromDegree(degree).name
        out.append(ChordCandidate(_symbol(root,quality),_roman_for_degree(degree,quality),frozenset(pitches),_FUNCTIONS[degree]))
    # Common seventh variants requested for V1: ii7, V7, viiø7.
    for degree,quality in [(2,"minor"),(5,"major"),(7,"diminished")]:
        pitches=[k.pitchFromDegree(degree+i*2).pitchClass for i in range(4)]
        root=k.pitchFromDegree(degree).name
        out.append(ChordCandidate(_symbol(root,quality,True),_roman_for_degree(degree,quality,True),frozenset(pitches),_FUNCTIONS[degree]))
    return out
