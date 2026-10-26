# v0.12.0 Full-corpus preflight audit

Read-only audit of all records, with separate deterministic full manifests for each original split. Does **not** merge splits or modify frozen EMH. No harmony generation occurs.

Run from `HARMONIX/`:

```bash
python -m pytest tests/ -q
python -m harmonix.corpus_audit --output results/corpus_audit.json --manifest-dir results/corpus_manifests
```

Send back `results/corpus_audit.json` first. Do **not** run full structural preservation over 2,000 records yet: v0.11 enumerates every possible intervention per song and would require many costly optimizer reruns. We must first implement a scalable evaluation engine and group-safe split audit. Generated manifests are **preflight** lists, not confirmed processable songs.

Existing inspected TEST data must remain exploratory; a fresh holdout should be constructed at work/group level where possible, using original TRAIN/DEV records and avoiding leakage through duplicate song identities. Artist/song metadata are imperfect proxies for work identity. No claims of independent composer count should be made from raw record counts.
