from pathlib import Path
from emh.musicxml_loader import load_musicxml

def test_harmony_annotations_are_ignored(tmp_path):
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
<part-list><score-part id="P1"><part-name>Melody</part-name></score-part></part-list>
<part id="P1"><measure number="1">
<attributes><divisions>1</divisions><key><fifths>0</fifths></key>
<time><beats>4</beats><beat-type>4</beat-type></time></attributes>
<harmony><root><root-step>C</root-step></root><kind>major</kind></harmony>
<note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note>
</measure></part></score-partwise>"""
    p = tmp_path / "with_harmony.musicxml"
    p.write_text(xml)
    data = load_musicxml(p)
    assert len(data.notes) == 1
    assert data.notes[0].pitch == "C4"
