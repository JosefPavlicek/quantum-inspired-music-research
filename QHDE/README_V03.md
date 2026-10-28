# QHDE v0.3 – corrected HARMONIX scoring bridge (experimental patch)

Place `qhde_harmonix_bridge.py` inside the existing top-level `QHDE/` directory. Does not modify HARMONIX or frozen `Explainable_Melody_Harmonizer/`.

The new bridge exports the **exact corrected candidate vocabulary** from `harmonix.knowledge_candidates.generate(..., 'corrected')`, and invokes **existing frozen EMH scoring functions** for every pair of two preprocessed segments. It preserves the rest-only transition prohibition and treats the *second segment as final*. Therefore a two-segment excerpt is a self-contained optimization problem, **not automatically a faithful score for a window embedded in a longer song**.

Expected invocation (from repo root in Codespaces, after input segmentation has been prepared using the same HARMONIX processing pipeline):

```python
from QHDE.qhde_harmonix_bridge import pair_scores, save_scores
# `segments`, `key`, `scale`, `config` must be obtained from HARMONIX's existing loader,
# segmentation, key-detection and config path, not constructed ad hoc.
result = pair_scores(segments[:2], key.tonic, key.mode, scale, config)
save_scores('QHDE/results/v03/corrected_pairs.json',result)
```

The HARMONIX `harmonix` module and frozen `emh` scorer must be importable; use HARMONIX's environment or its existing initialization routines. No QPU calls in this patch.

**Research caveats:** Corrected major/minor vocabulary currently has **10 candidates**, hence 100 pairs (or fewer if rest constraints apply). A uniform index encoding would need **7 qubits** (128 computational states), with 28 invalid states explicitly excluded. Do **not** silently reduce to 4 candidate chords (which would change the corrected vocabulary). A Qiskit/QAOA Hamiltonian, preservation of the score schema used by QHDE v0.2, and an end-to-end corpus exporter remain to be implemented and tested. `score` here is a real-valued local objective, not a claim of human preference.
