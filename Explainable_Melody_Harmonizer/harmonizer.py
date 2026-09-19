"""Command-line entry point for Explainable Melody Harmonizer."""

import argparse


def main():
    parser = argparse.ArgumentParser(description="Explainable Melody Harmonizer")
    parser.add_argument("--input", required=True, help="Monophonic MusicXML input")
    parser.add_argument("--config", default="config.yaml", help="Configuration file")
    parser.add_argument("--output", default="results", help="Output directory")
    args = parser.parse_args()

    print("EMH project skeleton is ready.")
    print(f"Input:  {args.input}")
    print(f"Config: {args.config}")
    print(f"Output: {args.output}")
    print("Harmonization pipeline will be implemented incrementally.")


if __name__ == "__main__":
    main()
