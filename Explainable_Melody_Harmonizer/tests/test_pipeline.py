import json
from pathlib import Path
from emh.pipeline import harmonize_musicxml
from emh.explanation import export_json,export_csv
F=Path(__file__).parent/"fixtures"

def test_end_to_end_4_4_returns_two_decisions():
 d=harmonize_musicxml(F/"test_4_4.musicxml")
 assert len(d)==2

def test_end_to_end_12_8_returns_four_decisions():
 d=harmonize_musicxml(F/"test_12_8.musicxml")
 assert len(d)==4

def test_json_export_contains_explanation(tmp_path):
 d=harmonize_musicxml(F/"test_4_4.musicxml"); p=tmp_path/"x.json"; export_json(d,p)
 data=json.loads(p.read_text())
 assert {"roman","melody_compatibility","functional_transition","local_score","path_score","alternatives"} <= set(data[0])

def test_csv_export_created(tmp_path):
 d=harmonize_musicxml(F/"test_4_4.musicxml"); p=tmp_path/"x.csv"; export_csv(d,p)
 assert p.exists() and "roman" in p.read_text()
