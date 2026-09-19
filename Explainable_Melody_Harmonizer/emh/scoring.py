"""Explicit and explainable scoring functions.

Conceptual local score:

S_t(p, c) =
    w_M * M(c, segment_t)
  + w_F * F(p, c)
  + w_R * R(p, c)
  + w_C * C(p, c, position_t)

Metric strength is incorporated into melody compatibility rather than
double-counted as an independent score.
"""


def melody_compatibility(segment, chord, key, config):
    raise NotImplementedError


def functional_transition(previous_chord, chord, config):
    raise NotImplementedError


def persistence(previous_chord, chord, config):
    raise NotImplementedError


def cadential_score(previous_chord, chord, position, config):
    raise NotImplementedError
