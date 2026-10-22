"""Run a pinned, local EMH copy in a separate Python process.

No imports from the sibling Explainable_Melody_Harmonizer project.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "emh_baseline"
MANIFEST = ROOT / "vendor" / "emh_sha256.json"

def verify_snapshot():
    expected = json.loads(MANIFEST.read_text(encoding="utf-8"))
    changes = []
    for name, digest in expected.items():
        file = VENDOR / name
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != digest:
            changes.append(name)
    if changes:
        raise RuntimeError("EMH baseline snapshot changed or missing: " + ", ".join(changes))
    return len(expected)

def run_baseline(input_file, output_dir):
    verify_snapshot()
    inp = Path(input_file).resolve()
    if not inp.is_file():
        raise FileNotFoundError(inp)
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "harmonizer.py", "--input", str(inp),
           "--config", "config.yaml", "--output", str(out)]
    subprocess.run(cmd, cwd=VENDOR, check=True)
    return out
