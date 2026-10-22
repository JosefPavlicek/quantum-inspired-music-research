#!/usr/bin/env python3
"""Copy HookTheory to shared data; never alter original EMH files."""
from pathlib import Path
import argparse
import hashlib
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Explainable_Melody_Harmonizer" / "data" / "hooktheory" / "Hooktheory.json.gz"
TARGET = ROOT / "data" / "hooktheory" / "Hooktheory.json.gz"
IGNORE = ROOT / ".gitignore"
RULE = "/data/*"

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser(description="Set up shared HookTheory copy without changing EMH")
    parser.add_argument("--copy", action="store_true", help="Copy existing EMH archive into shared data")
    args = parser.parse_args()
    if not SOURCE.is_file():
        raise SystemExit(f"Original archive not found: {SOURCE}; EMH was not changed")
    if TARGET.exists() and digest(SOURCE) != digest(TARGET):
        raise SystemExit("Existing shared archive differs from EMH; nothing was changed")
    if not args.copy:
        print(f"Source (untouched): {SOURCE}")
        print(f"Destination: {TARGET}")
        print("Dry run only; use --copy to create independent shared copy")
        return
    # Set ignore rule BEFORE creating the shared dataset; original EMH remains untouched.
    current = IGNORE.read_text(encoding="utf-8") if IGNORE.exists() else ""
    if RULE not in current.splitlines():
        with IGNORE.open("a", encoding="utf-8") as f:
            f.write(("\n" if current and not current.endswith("\n") else "") +
                    "# Shared datasets for new research projects\n/data/*\n!/data/README.md\n")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if not TARGET.exists():
        shutil.copy2(SOURCE, TARGET)
    print(f"Shared archive ready: {TARGET} (SHA256 {digest(TARGET)})")
    print(f"Original EMH archive remains unchanged: {SOURCE}")

if __name__ == "__main__":
    main()
