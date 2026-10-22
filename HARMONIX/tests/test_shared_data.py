from pathlib import Path
import pytest
from harmonix.shared_data import data_root, hooktheory_path, require_hooktheory

def test_default_data_location(monkeypatch):
    monkeypatch.delenv("MUSIC_RESEARCH_DATA", raising=False)
    assert hooktheory_path() == data_root() / "hooktheory" / "Hooktheory.json.gz"
    assert data_root().name == "data"

def test_override(monkeypatch, tmp_path):
    monkeypatch.setenv("MUSIC_RESEARCH_DATA", str(tmp_path))
    assert hooktheory_path() == tmp_path / "hooktheory" / "Hooktheory.json.gz"

def test_missing_file_explains_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("MUSIC_RESEARCH_DATA", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="setup_shared_data"):
        require_hooktheory()

def test_existing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("MUSIC_RESEARCH_DATA", str(tmp_path))
    p = tmp_path / "hooktheory" / "Hooktheory.json.gz"
    p.parent.mkdir()
    p.write_bytes(b"example")
    assert require_hooktheory() == p
