# HARMONIX

**Human-Aware Reasoning for Musical Optimization and eXplainability**

Long-term research platform for explainable computational harmonic decisions
and preservation of human musical intent. Independent of CAiSE or any journal.

## Isolation design

- `Explainable_Melody_Harmonizer/` remains unchanged in the repository.
- `HARMONIX/vendor/emh_baseline/` is a **frozen source snapshot** copied from
  the user-provided EMH archive. It is *not* imported from the sibling project.
- `harmonix/baseline.py` launches this snapshot in a separate Python process.
  The source snapshot is SHA-256 checked before each execution.
- Future HARMONIX logic belongs in `harmonix/`, never in `vendor/`.
- Changes in either project cannot silently alter the other's source code.
  They may still share the same Python environment unless you create a separate venv.

## Installation (from HARMONIX directory)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
python -m harmonix.cli verify-baseline
python -m pytest -q tests
```

## Run original baseline through HARMONIX

```bash
python -m harmonix.cli baseline --input fixtures/LaBamba_melody.musicxml --output results/baseline
```

The original baseline writes its normal CSV/JSON results under `results/baseline/`.
This is a **baseline adapter**, not a new HARMONIX harmonization algorithm.

## Next steps

Audit EMH modules, specify intent constraints and intervention API, add a
separate HARMONIX candidate/scoring/optimization path, then run controlled
comparisons. Do not change the frozen baseline.

## Provenance

Source snapshot: `EMH_CAiSE_2027.zip` supplied by the researcher.
`vendor/emh_sha256.json` records each copied baseline source/config/test file.
