# HARMONIX v0.5 — one-oracle-chord evaluation

**Scientific status:** evaluation machinery, not a positive experimental finding.

1. Select one segment **without access to reference chords**, using the largest
   achievable number of changed positions across forced EMH candidate chords.
2. Reveal the reference chord at that segment as a *simulated oracle response*.
3. Re-optimize the entire path with that chord fixed.
4. Measure **exact Roman-chord agreement** with held-out reference.
5. Compute the **exact expectation** for uniform-random selection of one
   feasible segment by evaluating every segment after selection. These
   post-hoc evaluations MUST NOT feed back into the selection rule.

**Reference format:** JSON array with exactly one EMH Roman chord per segment,
for example `["I", "IV", "V", "I"]`. Chord vocabulary must match the
frozen EMH candidates. Align the reference to EMH segments (typically two
per bar) before evaluation; do not assume a score's original chord labels
are automatically aligned.

**Caveats:** Exact-chord agreement is not musical quality. The oracle
intervention supplies one true reference chord; the reference is hidden
only for selecting its position, not for performing the intervention.
A maximum-sensitivity heuristic might perform worse than random. Uniform
random expectation is averaged over feasible positions for the SAME song;
it is not a multi-song significance test. Structural sensitivity can be
inflated by near-tied global paths. An alternative policy and independent
corpus should be preregistered before confirmatory claims.

**Usage** (from HARMONIX directory):

    python -m harmonix.oracle_experiment fixtures/LaBamba_melody.musicxml \\
      --reference references/labamba_roman.json \\
      --output results/labamba_oracle.json

The reference file must be constructed from an independently sourced,
verified transcription; it is intentionally NOT bundled or invented.
