# Shared datasets for HARMONIX and future projects

The original EMH project is immutable. Its files, data paths and README remain unchanged.

Canonical shared path: `data/hooktheory/Hooktheory.json.gz`.

From repository root run `python scripts/setup_shared_data.py --copy` to copy the
existing EMH archive into shared data, leaving the original in place.
The shared `data/` directory is ignored by Git, except `data/README.md`.
A separate shared copy intentionally uses more local disk space, but preserves
EMH as an independent, reproducible project. New projects may set the
`MUSIC_RESEARCH_DATA` environment variable to point at another shared directory.

The original public download URL, exact version and redistribution license of
this specific archive have not yet been verified. Document these before
publishing; do not distribute the archive in Git.
