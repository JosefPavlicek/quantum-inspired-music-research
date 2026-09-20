"""Command-line interface for Explainable Melody Harmonizer."""
import argparse
from pathlib import Path
import yaml
from emh.pipeline import harmonize_musicxml
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
    decisions=harmonize_musicxml(args.input,cfg)
    stem=Path(args.input).stem
    export_json(decisions,out/f"{stem}_decisions.json")
    export_csv(decisions,out/f"{stem}_decisions.csv")
    print(" | ".join(f"m{d.segment.measure}:{d.selected.symbol}({d.selected.roman})" for d in decisions))
    print(f"Decision log: {out}")

if __name__=="__main__": main()
