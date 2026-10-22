"""Read-only EMH scoring adapter and exact time-dependent counterfactual optimizer.

The frozen EMH package is imported ONLY in a separate worker process. Reference
chords are never loaded. All interventions force a *candidate chord* at one
segment and globally reoptimize every other segment.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'vendor' / 'emh_baseline'


@dataclass(frozen=True)
class HarmonicPath:
    choices: tuple[str, ...]
    score: float


@dataclass(frozen=True)
class HarmonicIntervention:
    position: int
    measure: int
    beat: str
    original: str
    forced: str
    changed_positions: tuple[int, ...]
    score_loss: float
    path: HarmonicPath

    @property
    def influence(self) -> int:
        return len(self.changed_positions)


class EMHDecisionGraph:
    """Exact additive EMH score graph, including time-dependent cadence/rest rules."""
    def __init__(self, data: Mapping):
        self.chords = tuple(data['chords'])
        self.segments = tuple(data['segments'])
        self.initial = dict(data['initial'])
        self.edges = tuple(dict(row) for row in data['edges'])
        if not self.chords or not self.segments or len(self.edges) != len(self.segments) - 1:
            raise ValueError('Invalid EMH graph dimensions')
        if len(set(self.chords)) != len(self.chords):
            raise ValueError('Chord IDs must be unique')
        priority = {'I': 0, 'V': 1, 'IV': 2, 'vi': 3, 'ii': 4, 'iii': 5,
                    'V7': 6, 'ii7': 7, 'vii°': 8, 'viiø7': 9}
        self._priority = {name: priority.get(name, 100) for name in self.chords}

    def optimize(self, forced: Mapping[int, str] | None = None) -> HarmonicPath:
        forced = dict(forced or {})
        for t, chord in forced.items():
            if not isinstance(t, int) or t < 0 or t >= len(self.segments) or chord not in self.chords:
                raise ValueError('Invalid forced chord or position')
        previous = {c: (score, (c,)) for c, score in self.initial.items()
                    if 0 not in forced or c == forced[0]}
        if not previous:
            raise ValueError('No feasible initial state')
        for t, edges in enumerate(self.edges, start=1):
            current = {}
            for c in self.chords:
                if t in forced and c != forced[t]:
                    continue
                best = None
                for p in self.chords:
                    if p not in previous or f'{p}\t{c}' not in edges:
                        continue
                    prior_score, prior_path = previous[p]
                    value = (prior_score + edges[f'{p}\t{c}'], prior_path + (c,))
                    if best is None or value[0] > best[0] + 1e-12:
                        best = value
                    # On ties, EMH prefers predecessor by candidate priority
                    elif abs(value[0] - best[0]) <= 1e-12 and self._priority[p] < self._priority[best[1][-2]]:
                        best = value
                if best is not None:
                    current[c] = best
            if not current:
                raise ValueError(f'No feasible harmonic path at segment {t}')
            previous = current
        winner = None
        for c in self.chords:
            if c not in previous:
                continue
            value = previous[c]
            if (winner is None or value[0] > winner[0] + 1e-12
                    or (abs(value[0] - winner[0]) <= 1e-12
                        and self._priority[c] < self._priority[winner[1][-1]])):
                winner = value
        assert winner is not None
        return HarmonicPath(winner[1], winner[0])

    def interventions(self) -> tuple[HarmonicIntervention, ...]:
        baseline = self.optimize()
        out = []
        for t, seg in enumerate(self.segments):
            for c in self.chords:
                if c == baseline.choices[t]:
                    continue
                try:
                    path = self.optimize({t: c})
                except ValueError:
                    continue
                changed = tuple(i for i, (a, b) in enumerate(zip(baseline.choices, path.choices)) if a != b)
                out.append(HarmonicIntervention(t, int(seg['measure']), str(seg['beat']),
                                                baseline.choices[t], c, changed,
                                                baseline.score - path.score, path))
        return tuple(out)

    def rank_positions(self) -> tuple[tuple[int, int], ...]:
        maxima = {t: 0 for t in range(len(self.segments))}
        for iv in self.interventions():
            maxima[iv.position] = max(maxima[iv.position], iv.influence)
        return tuple(sorted(maxima.items(), key=lambda x: (-x[1], x[0])))


def load_emh_graph(musicxml: str | Path) -> tuple[EMHDecisionGraph, dict]:
    """Verify the frozen vendor then extract scores in a separate subprocess."""
    from .baseline import verify_snapshot
    verify_snapshot()
    path = Path(musicxml).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    worker = Path(__file__).with_name('_emh_graph_worker.py')
    proc = subprocess.run([sys.executable, str(worker), str(path)], cwd=VENDOR,
                          check=True, capture_output=True, text=True)
    data = json.loads(proc.stdout)
    return EMHDecisionGraph(data), data


def main():
    parser = argparse.ArgumentParser(description='Reference-blind EMH decision influence')
    parser.add_argument('musicxml', help='Monophonic melody MusicXML')
    parser.add_argument('--output', help='JSON report path')
    args = parser.parse_args()
    graph, data = load_emh_graph(args.musicxml)
    baseline = graph.optimize()
    # Explicit parity check: do not publish measurements if bridge differs from EMH.
    if list(baseline.choices) != data['emh_baseline']:
        raise RuntimeError('Bridge path differs from frozen EMH; investigate before measuring')
    ranked = graph.rank_positions()
    report = {
        'source': str(Path(args.musicxml).resolve()), 'detected_key': data['detected_key'],
        'segments': data['segments'], 'baseline': list(baseline.choices),
        'baseline_score': baseline.score, 'parity_with_emh': True,
        'ranking': [{'position': t, 'measure': data['segments'][t]['measure'],
                     'beat': data['segments'][t]['beat'], 'maximum_changed_positions': n}
                    for t, n in ranked],
        'interventions': [{'position': x.position, 'measure': x.measure, 'beat': x.beat,
                           'original': x.original, 'forced': x.forced,
                           'changed_positions': list(x.changed_positions),
                           'influence': x.influence, 'score_loss': x.score_loss,
                           'counterfactual': list(x.path.choices)}
                          for x in graph.interventions()],
        'methodology': 'reference-blind; structural sensitivity only; not quality or improvement'
    }
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized + '\n', encoding='utf-8')
        print(f'Wrote {output}: {len(baseline.choices)} segments, {len(report["interventions"])} interventions')
    else:
        print(serialized)


if __name__ == '__main__':
    main()
