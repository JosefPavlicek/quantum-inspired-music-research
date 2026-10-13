# HookTheory × EMH v0.12 — frozen PoC audit

Processed cases: **19**; evaluated segments: **439**; excluded: **1**.

| Mutually exclusive segment outcome | Count | Percent |
|---|---:|---:|
| Exact chord match | 90 | 20.50% |
| Human chord not in EMH candidate set | 203 | 46.24% |
| Available but not selected | 146 | 33.26% |

Root agreement: **139/439 (31.66%)**.
Function agreement: **200/420 (47.62%)**.
Reference chord mixed within segment: **40**; incomplete reference coverage: **4**.

## Interpretation

These three categories distinguish representational limits from selection differences; they do not prove why an available chord was not selected.
Human reference is assigned by maximum temporal overlap. Functional agreement uses EMH-derived tonal context and is not independent human-function ground truth.
No EMH code or parameters were modified by this audit.

## Reproducibility

`python experiments/audit_hooktheory_poc.py --output results/hooktheory --core emh`

Generated: `diagnostics.json`, `diagnostics.md`.
