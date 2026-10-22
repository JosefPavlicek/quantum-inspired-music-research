# Upgrade from HARMONIX v0.1.0

Copy this ZIP’s `HARMONIX/` directory over the existing `HARMONIX/` directory. Existing files not in this patch are preserved, including the entire frozen EMH baseline.

From repository root:

```bash
cd HARMONIX
python -m pytest -q tests
python -m harmonix.cli verify-baseline
cd ..
git add HARMONIX/
git commit -m "Add independent harmonic knowledge model and notation tests"
git push origin main
```

After successful verification and push, optionally tag `harmonix-v0.2.0`.
