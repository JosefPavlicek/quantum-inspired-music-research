# QHDE v0.20 – Complexity–Depth Audit

**Backend/job:** ibm_pittsburgh / `dbh5k4pt9uhs73c9h07g`
**Cases:** 16; distinct centered landscapes: **14**; distinct affine-normalized landscapes: **14**.
**Full 100-pair optimum present in reduced task:** 7/16

## Hardware optimum-hit probability (macro mean across clips)

| Model | Mean measured P(optimum) |
|---|---:|
| uniform | 10.25% |
| p1 | 33.33% |
| p2 | 42.70% |
| p3 | 51.10% |

## Best depth (highest measured optimum-hit probability)

{'p3': 12, 'p2': 3, 'p1': 1}

## Exact duplicate score landscapes (after subtracting mean)

[['WeglOnvlmrY', 'dPoD-yjqmnM', 'dPoDJekZgnM']]

## Affine-normalized identical landscapes (after min-max normalization)

[['WeglOnvlmrY', 'dPoD-yjqmnM', 'dPoDJekZgnM']]

These are grouping diagnostics, not proof that two songs are the same. Affine normalization is only a comparison heuristic; it does not preserve dynamics at fixed QAOA gamma.

## Per-stratum averages

| Stratum | N | uniform | p1 | p2 | p3 |
|---|---:|---:|---:|---:|---:|
| high_entropy__high_repetition | 4 | 9.57% | 25.02% | 31.30% | 37.92% |
| high_entropy__low_repetition | 4 | 13.09% | 37.65% | 53.10% | 59.47% |
| low_entropy__high_repetition | 4 | 7.89% | 32.18% | 44.85% | 51.73% |
| low_entropy__low_repetition | 4 | 10.47% | 38.45% | 41.55% | 55.27% |

## Exploratory correlations (Spearman; unadjusted two-sided permutation tests)

| Feature | Outcome | rho | p |
|---|---|---:|---:|
| chord_entropy_bits | delta_31 | 0.338 | 0.1924 |
| chord_entropy_bits | delta_32 | 0.138 | 0.6096 |
| chord_entropy_bits | noise_gap_p3 | 0.068 | 0.7954 |
| conditional_transition_entropy_bits | delta_31 | -0.130 | 0.6340 |
| conditional_transition_entropy_bits | delta_32 | -0.307 | 0.2512 |
| conditional_transition_entropy_bits | noise_gap_p3 | 0.224 | 0.3962 |
| repeated_bigram_rate | delta_31 | -0.197 | 0.4572 |
| repeated_bigram_rate | delta_32 | 0.008 | 0.9760 |
| repeated_bigram_rate | noise_gap_p3 | -0.004 | 0.9902 |
| n_chords | delta_31 | -0.016 | 0.9540 |
| n_chords | delta_32 | -0.058 | 0.8334 |
| n_chords | noise_gap_p3 | 0.192 | 0.4778 |

## Interpretation safeguards

- 16 selected TRAIN clips, not independent held-out data
- full-clip harmonic features versus only first-two-segment optimization
- near-duplicate scoring landscapes may reduce effective sample size
- QAOA classical parameters optimized per task and depth; optimizer budget not controlled here
- one QPU job, no repeated randomized calibration-drift blocks
- model-score optimum over 16 states; not human-perceived musical quality
- multiple exploratory correlation tests; unadjusted permutation p-values; not confirmatory inference
- exact classical enumeration of 16 states is trivial; no quantum advantage claim

**This report is descriptive/exploratory, not evidence of musical complexity determining useful circuit depth.**
