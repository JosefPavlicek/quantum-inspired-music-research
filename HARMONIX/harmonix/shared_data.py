"""Find shared music corpora without coupling to a specific research project."""
from __future__ import annotations
import os
from pathlib import Path

def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]

def data_root() -> Path:
    override = os.environ.get("MUSIC_RESEARCH_DATA")
    return Path(override).expanduser().resolve() if override else repository_root() / "data"

def hooktheory_path() -> Path:
    return data_root() / "hooktheory" / "Hooktheory.json.gz"

def require_hooktheory() -> Path:
    path = hooktheory_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"HookTheory archive not found: {path}. "
            "Run: python scripts/setup_shared_data.py --move --link-legacy "
            "(from repository root), or configure MUSIC_RESEARCH_DATA."
        )
    return path
