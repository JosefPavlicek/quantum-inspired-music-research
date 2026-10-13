"""Dataset loading and strict generation/reference separation."""
import gzip, json

def load_dataset(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)

def melody_only(record):
    a=record["annotations"]
    return {"num_beats":a["num_beats"], "meters":a["meters"],
            "melody":[dict(e) for e in a["melody"]]}

def reference_only(record):
    return [dict(e) for e in record["annotations"]["harmony"]]
