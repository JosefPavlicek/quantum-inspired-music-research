# HARMONIX 0.4: frozen-EMH decision graph

- **Read-only isolation:** the vendor is checked against SHA-256 manifest before extraction. Worker imports vendor code only in a child process.
- **Reference firewall:** only melody notes are loaded; EMH's MusicXML loader ignores `<harmony>` annotations. No reference harmony enters scoring or ranking.
- **Exact scoring:** reproduce the initial score and all time-dependent predecessor-to-current scores from EMH's existing scoring functions. Preserve rest-only transitions, cadence on final segment, detected key, and candidate order.
- **Parity gate:** refuse to emit reports unless the unconstrained graph optimum equals frozen EMH's own optimizer output on the same melody.
- **Intervention:** force one *candidate chord identity* at one segment; optimize all other positions globally.
- **Metric:** structural influence = count of changed chord decisions across the entire sequence, including the forced segment. Report the score loss relative to the unconstrained optimum. This is not proof of better harmony.
- **Known limits:** frozen EMH's candidate vocabulary contains no inversions; HARMONIX knowledge model supports them but integration comes later. Interventions are counterfactual simulations, not human feedback. No reference-quality gain is claimed. Candidate alternatives are enumerated; large pieces may be computationally expensive.

## Usage from `HARMONIX/`

```bash
python -m harmonix.emh_bridge fixtures/LaBamba_melody.musicxml --output results/labamba_influence.json
python -m pytest -q tests
python -m harmonix.cli verify-baseline
```

Do not overwrite or delete `harmonix/`, `tests/`, or `docs/` when extracting this patch. From repository root use `unzip -n HARMONIX_v0.4.0_patch.zip` (or `unzip -o` only after reviewing file list); the archive contains **only new files**.
