# Upgrade to v0.3.0

Extract this ZIP at the repository root. It **only adds** three files under HARMONIX/:
- harmonix/counterfactual.py
- tests/test_counterfactual.py
- docs/COUNTERFACTUAL_PROTOCOL.md

No existing files are overwritten. The EMH baseline is untouched.

From the HARMONIX directory:

```bash
python -m pytest -q tests
python -m harmonix.cli verify-baseline
```

After success, commit and tag v0.3.0.
