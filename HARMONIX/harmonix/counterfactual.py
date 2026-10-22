"""Reference-blind global counterfactual analysis of sequential harmonic choices.

A small, independent dynamic-programming kernel. EMH snapshot is not modified.
All scores are supplied explicitly; no reference chords are used for ranking.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Mapping, Sequence


@dataclass(frozen=True)
class PathResult:
    choices: tuple[str, ...]
    score: float


@dataclass(frozen=True)
class Intervention:
    position: int
    forced_choice: str
    baseline_choice: str
    changed_positions: tuple[int, ...]
    score_loss: float
    counterfactual: PathResult

    @property
    def influence(self) -> int:
        return len(self.changed_positions)


class SequentialModel:
    """A finite-state first-order maximization model.

    local[t][choice] gives the local score; transitions[(prev, current)]
    gives the transition score, identical across time. Missing transitions
    are forbidden. Ties are broken lexicographically and deterministically.
    """

    def __init__(self, local: Sequence[Mapping[str, float]], transitions: Mapping[tuple[str, str], float]):
        if not local or any(not row for row in local):
            raise ValueError('At least one nonempty decision step is required')
        self.local = tuple(dict(row) for row in local)
        self.transitions = dict(transitions)
        if any(not isfinite(v) for row in self.local for v in row.values()):
            raise ValueError('Local scores must be finite')
        if any(not isfinite(v) for v in self.transitions.values()):
            raise ValueError('Transition scores must be finite')

    def optimize(self, forced: Mapping[int, str] | None = None) -> PathResult:
        forced = dict(forced or {})
        if any(not isinstance(t, int) or t < 0 or t >= len(self.local) or c not in self.local[t]
               for t, c in forced.items()):
            raise ValueError('Forced choice must exist at its position')
        # Each state stores (score, full path) for deterministic tie breaking.
        previous: dict[str, tuple[float, tuple[str, ...]]] = {}
        for t, row in enumerate(self.local):
            current = {}
            for choice in sorted(row):
                if t in forced and choice != forced[t]:
                    continue
                if t == 0:
                    current[choice] = (row[choice], (choice,))
                else:
                    possibilities = [(score + self.transitions[(prior, choice)] + row[choice],
                                      path + (choice,))
                                     for prior, (score, path) in previous.items()
                                     if (prior, choice) in self.transitions]
                    if possibilities:
                        current[choice] = sorted(possibilities, key=lambda x: (-x[0], x[1]))[0]
            if not current:
                raise ValueError(f'No feasible path at position {t}')
            previous = current
        score, path = sorted(previous.values(), key=lambda x: (-x[0], x[1]))[0]
        return PathResult(path, score)

    def interventions(self) -> tuple[Intervention, ...]:
        """Enumerate every feasible single-position alternative to baseline."""
        baseline = self.optimize()
        result = []
        for t, row in enumerate(self.local):
            for choice in sorted(row):
                if choice == baseline.choices[t]:
                    continue
                try:
                    cf = self.optimize({t: choice})
                except ValueError:
                    continue
                changed = tuple(i for i, (a, b) in enumerate(zip(baseline.choices, cf.choices)) if a != b)
                result.append(Intervention(t, choice, baseline.choices[t], changed,
                                           baseline.score - cf.score, cf))
        return tuple(result)

    def rank_positions(self) -> tuple[tuple[int, int], ...]:
        """Rank by maximum changed positions under a feasible single intervention.

        This is structural *sensitivity*, not expected target improvement.
        """
        maxima = {t: 0 for t in range(len(self.local))}
        for intervention in self.interventions():
            maxima[intervention.position] = max(maxima[intervention.position], intervention.influence)
        return tuple(sorted(maxima.items(), key=lambda item: (-item[1], item[0])))


def reference_distance(path: Sequence[str], reference: Sequence[str]) -> int:
    """Simple exact-choice Hamming distance; richer musical metrics come later."""
    if len(path) != len(reference):
        raise ValueError('Reference and prediction must have equal lengths')
    return sum(a != b for a, b in zip(path, reference))


def evaluate_intervention(intervention: Intervention, baseline: PathResult,
                          reference: Sequence[str]) -> dict[str, int | float]:
    """Post-hoc evaluation only. Never call this from intervention selection."""
    before = reference_distance(baseline.choices, reference)
    after = reference_distance(intervention.counterfactual.choices, reference)
    return {'distance_before': before, 'distance_after': after,
            'gain': before - after, 'influence': intervention.influence,
            'score_loss': intervention.score_loss}
