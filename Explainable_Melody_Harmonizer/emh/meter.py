"""Meter and metric-strength handling."""
from fractions import Fraction

SUPPORTED_METERS={"2/4","3/4","4/4","6/8","12/8"}

def metric_strength(time_signature, beat):
    """Return transparent categorical metric weights for EMH scoring."""
    b=Fraction(beat)
    if time_signature=="4/4":
        return 1.5 if b==1 else (1.2 if b==3 else 1.0)
    if time_signature=="3/4":
        return 1.5 if b==1 else 1.0
    if time_signature=="2/4":
        return 1.5 if b==1 else 1.0
    if time_signature=="6/8":
        return 1.5 if b==1 else (1.2 if b==4 else 1.0)
    if time_signature=="12/8":
        return 1.5 if b==1 else (1.2 if b in {4,7,10} else 1.0)
    raise ValueError(f"Unsupported time signature: {time_signature}")
