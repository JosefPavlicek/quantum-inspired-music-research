# v0.5.0 additive update

Adds ONLY `harmonix/oracle_experiment.py`, `tests/test_oracle_experiment.py`,
`docs/ORACLE_PROTOCOL.md` and this note. No existing file is replaced.
Extract with `unzip -n` at repository root.

Run from HARMONIX:

    python -m pytest -q tests
    python -m harmonix.cli verify-baseline

Do not run the oracle experiment until a genuinely independent, correctly
aligned reference Roman-chord sequence is available.
