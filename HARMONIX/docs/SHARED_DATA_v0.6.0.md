# v0.6.0 corrected: EMH untouched

This replaces the earlier unsafe setup instructions. NEVER use --move or
--link-legacy. From repository root:

    python scripts/setup_shared_data.py --copy
    cd HARMONIX
    python -m pytest -q tests
    python -m harmonix.cli verify-baseline

No file inside Explainable_Melody_Harmonizer is changed. The setup only copies
an archive, modifies root .gitignore, and creates a shared data folder.
