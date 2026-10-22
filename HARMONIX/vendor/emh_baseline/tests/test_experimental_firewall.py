from pathlib import Path


def test_cli_has_no_reference_chord_argument():
    source = Path("harmonizer.py").read_text(encoding="utf-8")
    assert "--reference" not in source
    assert "--original-chords" not in source
