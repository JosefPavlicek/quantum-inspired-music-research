# QHDE v0.16 — independent music-descriptor audit

Input TRAIN records: 100; fully parsed chord sequences: 98.
No quantum job submitted. No harmonization scoring used in descriptors.

## Scope and limitations

- Descriptors use source *reference harmony*, NOT corrected EMH candidate scores.
- Chord identity combines root pitch class, ordered root-position intervals and inversion; not normalized for key or enharmonic notation.
- No inference about whole-song complexity from QHDE two-segment optimization.
- No blind prediction of ideal p is possible yet; next stage requires independent, held-out evaluation.
- Unsupported schemas are reported rather than silently treated as valid chord sequences.

## Parsed records (first 15)

| ID | Chords | Unique | Chord entropy (bits) | Transition entropy (bits) | Repeated bigrams |
|---|---:|---:|---:|---:|---:|
| LAgQGkwEoyO | 16 | 4 | 2.000 | 1.990 | 73.33% |
| bWgMvrVkxlX | 8 | 3 | 1.500 | 1.950 | 42.86% |
| DpgvlyPBoad | 21 | 18 | 4.107 | 4.322 | 0.00% |
| nZgWXMVQxry | 15 | 4 | 1.990 | 2.182 | 64.29% |
| RPxeyBjaxb_ | 27 | 10 | 3.010 | 4.027 | 30.77% |
| WeglnBNLorY | 8 | 3 | 1.561 | 1.950 | 42.86% |
| kygzpebnoKB | 14 | 4 | 1.484 | 1.881 | 61.54% |
| jDgXOR_nmKl | 16 | 2 | 1.000 | 0.997 | 86.67% |
| LAgQZWeAxyO | 14 | 6 | 2.522 | 2.777 | 46.15% |
| WeglOnvlmrY | 16 | 9 | 3.078 | 3.907 | 0.00% |
| jDgXNLlyoKl | 14 | 7 | 2.807 | 2.777 | 46.15% |
| ZOxVvdrZxdq | 30 | 5 | 1.873 | 2.582 | 72.41% |
| VMgJjLZKgqK | 20 | 8 | 2.841 | 3.195 | 47.37% |
| d_gwWQZNgGV | 13 | 8 | 2.777 | 3.585 | 0.00% |
| d_gwNeebmGV | 9 | 3 | 1.436 | 2.000 | 50.00% |

## Schema issues

2 records could not be reliably interpreted. Inspect `features.json` diagnostics before publishing.
