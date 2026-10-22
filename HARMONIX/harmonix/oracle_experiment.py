"""Reference-blind one-query intervention evaluation for EMH decision graphs.

Selection sees only the EMH graph. Reference is consulted AFTER selecting a position.
The reference chord at the selected position simulates a single oracle response.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Sequence

from .emh_bridge import EMHDecisionGraph, load_emh_graph


def exact_agreement(path: Sequence[str], reference: Sequence[str]) -> float:
    if len(path) != len(reference) or not path:
        raise ValueError("Reference length must match the nonempty segment sequence")
    return sum(a == b for a, b in zip(path, reference)) / len(reference)


def blind_rank(graph: EMHDecisionGraph) -> list[int]:
    """Maximum global sensitivity, stable tie-breaking by earliest position."""
    return [position for position, _ in graph.rank_positions()]


def evaluate_one_query(graph: EMHDecisionGraph, reference: Sequence[str]) -> dict:
    """Evaluate all positions post hoc, but select the intervention blindly.

    Random baseline is the EXACT expected outcome of uniformly selecting one
    feasible position; it is not one lucky/unlucky sampled random trial.
    """
    reference = tuple(reference)
    if len(reference) != len(graph.segments):
        raise ValueError(f"Expected {len(graph.segments)} reference chords, got {len(reference)}")
    unknown = sorted(set(reference) - set(graph.chords))
    if unknown:
        raise ValueError(f"Reference contains chords outside EMH candidate vocabulary: {unknown}")
    baseline = graph.optimize()
    base_agreement = exact_agreement(baseline.choices, reference)
    rank = blind_rank(graph)
    rows = []
    for position in range(len(reference)):
        try:
            outcome = graph.optimize({position: reference[position]})
        except ValueError:
            # A constraint may be impossible for a rest segment. Such a
            # position is not a feasible oracle-query opportunity.
            continue
        agreement = exact_agreement(outcome.choices, reference)
        rows.append({
            "position": position,
            "measure": graph.segments[position]["measure"],
            "beat": str(graph.segments[position]["beat"]),
            "reference_chord": reference[position],
            "baseline_chord": baseline.choices[position],
            "result": list(outcome.choices),
            "agreement": agreement,
            "gain": agreement - base_agreement,
            "changed_positions": [i for i,(a,b) in enumerate(zip(baseline.choices,outcome.choices)) if a != b],
        })
    by_pos = {r["position"]: r for r in rows}
    eligible = [p for p in rank if p in by_pos]
    if not eligible:
        raise ValueError("No feasible oracle intervention positions")
    selected = by_pos[eligible[0]]
    random_expectation = mean(by_pos[p]["agreement"] for p in eligible)
    # Every baseline is queried with the same one-reference-chord information.
    return {
        "protocol": "single oracle chord, position chosen reference-blind",
        "selection_rule": "maximum over candidate-forced global changed positions; earliest tie",
        "reference_used_for_selection": False,
        "segment_count": len(reference),
        "feasible_positions": len(eligible),
        "baseline": list(baseline.choices),
        "baseline_agreement": base_agreement,
        "selected_position": selected["position"],
        "selected": selected,
        "random_expected_agreement": random_expectation,
        "random_expected_gain": random_expectation - base_agreement,
        "advantage_over_uniform_random": selected["agreement"] - random_expectation,
        "all_positions_posthoc": rows,
        "caveat": "Exact chord agreement only; one oracle chord revealed after position selection. This does not measure perceived musical quality."
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate one reference-blind EMH oracle intervention")
    parser.add_argument("musicxml")
    parser.add_argument("--reference", required=True, help="JSON array of Roman chords, one per EMH segment")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    graph, data = load_emh_graph(args.musicxml)
    if list(graph.optimize().choices) != data["emh_baseline"]:
        raise RuntimeError("EMH baseline parity check failed")
    ref = json.loads(Path(args.reference).read_text(encoding="utf-8"))
    if not isinstance(ref, list) or not all(isinstance(c, str) for c in ref):
        raise ValueError("Reference must be a JSON array of Roman chord strings")
    report = evaluate_one_query(graph, ref)
    report["source"] = str(Path(args.musicxml).resolve())
    report["detected_key"] = data["detected_key"]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {output}; selected gain={report['selected']['gain']:+.3f}; "
          f"uniform-random expected gain={report['random_expected_gain']:+.3f}")


if __name__ == "__main__":
    main()
