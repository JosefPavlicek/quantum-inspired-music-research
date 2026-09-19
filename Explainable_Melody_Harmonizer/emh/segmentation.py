"""Harmonic decision-point segmentation.

Default conceptual grid:
2/4  -> one segment per measure
3/4  -> one segment per measure
4/4  -> beats 1-2 / 3-4
6/8  -> eighths 1-3 / 4-6
12/8 -> eighths 1-3 / 4-6 / 7-9 / 10-12
"""


def segment_notes(notes, time_signature, config):
    raise NotImplementedError("Meter-aware segmentation will be implemented next.")
