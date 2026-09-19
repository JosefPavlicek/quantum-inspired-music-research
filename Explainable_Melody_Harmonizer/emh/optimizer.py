"""Global dynamic-programming / Viterbi-like optimizer.

The optimizer must distinguish:
- local_score: contribution at the current harmonic decision
- path_score: accumulated globally optimized score
"""


def optimize(segments, candidates, scorer):
    raise NotImplementedError("Viterbi-like optimization will be implemented next.")
