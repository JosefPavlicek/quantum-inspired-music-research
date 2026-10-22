# HARMONIX v0.7.0 — HookTheory exploratory experiment

**EMH source, data and frozen HARMONIX baseline remain unchanged.**

Run from the `HARMONIX` directory after installing `music21` and other
existing EMH dependencies and setting up the shared dataset:

    python -m pytest -q tests
    python -m harmonix.cli verify-baseline
    python -m harmonix.hooktheory_experiment \
      --selection ../Explainable_Melody_Harmonizer/selection.json \
      --output results/hooktheory_oracle.json --limit 20

The selection must contain original EMH TEST IDs. The worker reads the
shared HookTheory archive, passes **melody only** to the frozen EMH
scoring graph and verifies baseline parity. Only after generation does it
read the human chord labels. Exact root and pitch-class-set matching maps
an annotation to a unique EMH candidate. Ambiguous, mixed, partial or
out-of-vocabulary reference labels are excluded from evaluation.

For each song, compare targeted max-influence query with exact uniform
random expected agreement over feasible query locations, with one
reference chord revealed per method. All scores use the same eligible
segments. Aggregates are song-weighted, not segment-weighted.

**Limitations**: Feasible positions are determined using reference
annotations after blind ranking, which can create selection bias.
The protocol is exploratory and not yet a fully reference-blind human
query experiment. Results do not measure perceived quality. A larger
independent validation set, alternate baselines, a coverage sensitivity
analysis and uncertainty estimates are needed before CAiSE claims.

If all songs are excluded, inspect the report's `reason` fields rather
than inventing numerical results.
