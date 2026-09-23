"""Command-line interface for Explainable Melody Harmonizer."""
import argparse, json
from pathlib import Path
import yaml
from emh.pipeline import harmonize_musicxml_with_metadata
from emh.explanation import export_json,export_csv

def build_parser():
    p=argparse.ArgumentParser(description="Explainable Melody Harmonizer")
    p.add_argument("--input",required=True)
    p.add_argument("--config",default="config.yaml")
    p.add_argument("--output",default="results")
    return p

def main():
    args=build_parser().parse_args()
    cfg={}
    cp=Path(args.config)
    if cp.exists(): cfg=yaml.safe_load(cp.read_text()) or {}
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    decisions,meta=harmonize_musicxml_with_metadata(args.input,cfg)
    stem=Path(args.input).stem
    export_json(decisions,out/f"{stem}_decisions.json")
    export_csv(decisions,out/f"{stem}_decisions.csv")
    key_data={
        "xml_key":meta.xml_key,
        "detected_key":meta.detected_key,
        "key_detection_score":meta.key_detection_score,
        "key_source":meta.key_source,
        "ranking":[{"key":k.name,"score":k.score} for k in meta.key_ranking],
    }
    (out/f"{stem}_key_detection.json").write_text(json.dumps(key_data,indent=2),encoding="utf-8")
    print(f"Key: {meta.detected_key} (score={meta.key_detection_score:.4f}); MusicXML={meta.xml_key}")
    print(" | ".join(f"m{d.segment.measure}:{d.selected.symbol}({d.selected.roman})" for d in decisions))
    print(f"Decision log: {out}")

if __name__=="__main__": main()
