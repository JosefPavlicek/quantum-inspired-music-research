# HARMONIX research plan

Core problem: preserve and explain human harmonic intent in computational harmonization.

Planned independent modules (NOT implemented yet):
1. Structured chord representation (root, quality, extensions, alterations, bass, omissions).
2. Human-intent constraints (hard/soft; musical function, persistence, cadence, tension).
3. Candidate-space vs selection-strategy diagnosis.
4. Explainable intervention and global re-optimization.
5. Controlled evaluation: frozen EMH baseline vs HARMONIX variants.

The vendor EMH copy is an immutable historical baseline, not the place for
implementing new features. New features belong in harmonix/.

Prevent reference leakage: original human chord labels may be used in evaluation
but not in generation unless an explicitly separate, documented intervention
experiment supplies user constraints. Keep evaluation and generation splits clear.
