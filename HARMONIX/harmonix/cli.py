import argparse
from pathlib import Path
from .baseline import verify_snapshot, run_baseline

def main():
    p = argparse.ArgumentParser(description="HARMONIX — independent research platform")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("verify-baseline")
    run = sub.add_parser("baseline")
    run.add_argument("--input", required=True)
    run.add_argument("--output", default="results/baseline")
    args = p.parse_args()
    if args.command == "verify-baseline":
        print(f"EMH snapshot OK: {verify_snapshot()} files")
    else:
        run_baseline(args.input, args.output)

if __name__ == "__main__":
    main()
