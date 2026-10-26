"""Descriptive, reference-aware diagnostics. Never use this module to select interventions."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

COMMON = {"major_triad", "minor_triad", "dominant_seventh",
          "minor_seventh", "major_seventh", "half_diminished_seventh"}
COMPLEX = {"extended_or_complex", "other_four_note", "sus4"}

def analyze(report: dict) -> dict:
    segments = report["segments"]
    statuses = Counter(s["status"] for s in segments)
    oov = [s for s in segments if s["status"] == "out_of_vocabulary"]
    by_quality = Counter(s.get("quality") or "unknown" for s in oov)
    by_root = Counter(str(s.get("root_pitch_class")) for s in oov)
    by_template = Counter(
        f"{s.get('quality','unknown')}:{','.join(map(str,s.get('relative_pitch_classes') or []))}"
        for s in oov
    )
    songs = defaultdict(lambda: Counter())
    for s in segments:
        songs[s["id"]][s["status"]] += 1
    common = sum(by_quality[k] for k in COMMON)
    complex_n = sum(by_quality[k] for k in COMPLEX)
    exact_root = sum(bool(s.get("root_match_any")) for s in oov)
    pc_match = sum(bool(s.get("pitch_class_match_any")) for s in oov)
    return {
        "method": "Descriptive reference-aware audit; NOT a blind intervention selector",
        "n_segments": len(segments),
        "n_songs_with_segments": len(songs),
        "n_worker_failures": len(report.get("failures", [])),
        "status_counts": dict(sorted(statuses.items())),
        "oov_count": len(oov),
        "oov_common_quality_count": common,
        "oov_complex_quality_count": complex_n,
        "oov_root_available_count": exact_root,
        "oov_pitch_class_available_count": pc_match,
        "oov_by_quality": dict(sorted(by_quality.items())),
        "oov_by_root_pitch_class": dict(sorted(by_root.items(), key=lambda x:int(x[0]) if x[0].isdigit() else 99)),
        "oov_top_templates": [{"template":k,"count":v} for k,v in by_template.most_common(15)],
        "per_song": [
            {"id": ident, "segments":sum(c.values()), "covered":c["covered"],
             "out_of_vocabulary":c["out_of_vocabulary"],
             "mixed_or_partial":c["mixed_or_partial"],"no_reference":c["no_reference"]}
            for ident,c in sorted(songs.items())
        ],
        "limitations": [
            "Reference labels are consulted: do not use these results to choose intervention locations.",
            "Root-present is not proof that a chord can be represented: chord quality and pitch-class sets matter.",
            "A missing pitch-class set does not identify the cause (candidate generation, key detection, or mapping).",
            "Inversions and voicing are not recoverable from pitch-class sets.",
            "No counterfactual candidate augmentation or causal improvement is established.",
            "Do not tune on TEST and then report an unbiased TEST evaluation.",
        ],
    }

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args=parser.parse_args(argv)
    data=analyze(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Analyzed {data['n_segments']} segments, {data['oov_count']} OOV; output: {args.output}")

if __name__=="__main__":
    main()
