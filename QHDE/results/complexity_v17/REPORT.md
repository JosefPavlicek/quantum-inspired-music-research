# QHDE v0.17 — independent music-complexity selection

Loaded 100 TRAIN clips; valid 98; eligible 81; selected 16.

## Strata

| Stratum | Eligible | Selected |
|---|---:|---:|
| low_entropy__high_repetition | 21 | 4 |
| low_entropy__low_repetition | 20 | 4 |
| high_entropy__high_repetition | 18 | 4 |
| high_entropy__low_repetition | 22 | 4 |

## Selected clips

| ID | Chords | H(next chord given current) | Repeated bigrams | Stratum |
|---|---:|---:|---:|---|
| dPoDrNVqgnM | 16 | 0.267 | 46.7% | low_entropy__high_repetition |
| LAgQnYKlxyO | 16 | 0.000 | 73.3% | low_entropy__high_repetition |
| QLgnvz_Yg-V | 16 | 0.000 | 73.3% | low_entropy__high_repetition |
| dPoD-yjqmnM | 16 | 0.400 | 46.7% | low_entropy__high_repetition |
| dPoDJekZgnM | 10 | 0.000 | 44.4% | low_entropy__low_repetition |
| jDgXQwLyxKl | 10 | 0.306 | 44.4% | low_entropy__low_repetition |
| AQodnNrqgDl | 10 | 0.222 | 0.0% | low_entropy__low_repetition |
| _NgbbeRrgQA | 11 | 0.400 | 10.0% | low_entropy__low_repetition |
| jDgXOMDnmKl | 27 | 0.759 | 61.5% | high_entropy__high_repetition |
| AQodGpPKxDl | 28 | 0.613 | 66.7% | high_entropy__high_repetition |
| ZOxVvdrZxdq | 30 | 0.863 | 72.4% | high_entropy__high_repetition |
| ANmpQAvngyM | 30 | 0.844 | 62.1% | high_entropy__high_repetition |
| zngRNKQegJj | 17 | 0.500 | 0.0% | high_entropy__low_repetition |
| WeglOnvlmrY | 16 | 0.800 | 0.0% | high_entropy__low_repetition |
| veoYWNOVgdn | 18 | 0.750 | 23.5% | high_entropy__low_repetition |
| yvmrdppJxOW | 15 | 0.482 | 7.1% | high_entropy__low_repetition |

## Study limits

- These are annotated HookTheory clips, not necessarily full compositions.
- Music-only selection avoids selecting based on favorable QAOA outcomes.
- Small samples and varying clip lengths/confounding remain. Strata can be sparse.
- No corrected-EMH QAOA instance has been generated for new clips yet.
- For each selected clip, generate a reference-blind score instance with the EXISTING corrected EMH bridge and an explicit fixed rule; do not assume v0.13 works on arbitrary clips.
- Freeze the selection/parameters before new QPU evaluation; use held-out data for stronger claims.
- No IBM API is called by this script.
