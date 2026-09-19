"""Meter and metric-strength handling.

Important design rule: compound meters remain compound.
6/8 and 12/8 are never rewritten merely to simplify computation.
"""

SUPPORTED_METERS = {"2/4", "3/4", "4/4", "6/8", "12/8"}


def metric_strength(time_signature, beat):
    raise NotImplementedError("Metric weighting will be implemented next.")
