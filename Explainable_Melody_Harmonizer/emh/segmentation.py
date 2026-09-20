"""Meter-aware harmonic segmentation for EMH."""
from fractions import Fraction
from emh.model import HarmonicSegment

def _measure_length(ts):
    num, den = map(int, ts.split("/"))
    return Fraction(num * 4, den)

def _boundaries(ts):
    # Offsets in quarterLength units from measure start.
    grids = {
        "2/4": [Fraction(0)],
        "3/4": [Fraction(0)],
        "4/4": [Fraction(0), Fraction(2)],
        "6/8": [Fraction(0), Fraction(3, 2)],
        "12/8": [Fraction(0), Fraction(3, 2), Fraction(3), Fraction(9, 2)],
    }
    if ts not in grids:
        raise ValueError(f"Unsupported time signature: {ts}")
    return grids[ts]

def segment_notes(notes, time_signatures, config=None):
    """Create harmonic segments without quantizing note durations.

    Notes are assigned by onset. Notes sustaining across a segment boundary
    remain represented by their original NoteEvent; overlap-aware scoring
    will account for the sounding fraction later.
    """
    if not notes:
        return []

    measures = sorted({n.measure for n in notes})
    result=[]
    idx=0
    for measure in measures:
        if measure not in time_signatures:
            raise ValueError(f"Missing time signature for measure {measure}")
        ts=time_signatures[measure]
        bounds=_boundaries(ts)
        length=_measure_length(ts)
        measure_notes=[n for n in notes if n.measure==measure]
        # music21 beat 1 corresponds to local offset 0.
        for j,start in enumerate(bounds):
            end=bounds[j+1] if j+1<len(bounds) else length
            selected=[]
            for n in measure_notes:
                local=n.beat-Fraction(1)
                if start <= local < end:
                    selected.append(n)
            result.append(HarmonicSegment(
                index=idx,
                measure=measure,
                start_beat=start+Fraction(1),
                duration=end-start,
                notes=selected,
            ))
            idx+=1
    return result
