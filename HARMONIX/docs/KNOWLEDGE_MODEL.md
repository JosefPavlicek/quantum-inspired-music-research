# HARMONIX v0.2.0 — Harmonic Knowledge Model

Independent of frozen `vendor/emh_baseline`.

- `Chord.harmonic_identity()`: root, quality, pitch intervals (ignores bass and voicing).
- `Chord.realization_identity()`: harmonic identity + bass.
- `Chord.inversion`: classical inversion index for triads and sevenths; returns `None` for a nonstructural bass.
- `Voicing`: absolute MIDI notes, distinct from harmonic identity.
- `classify_change`: purely structural change classification; **not** a human-intent metric.
- `notation.py`: simplified chord and Nashville labels, not internal keys.

## Deliberate limitations

- Chromatic pitch classes alone cannot retain enharmonic spelling (F# vs Gb). Later versions require diatonic spelling and key context.
- Nashville rendering currently assumes a major-key reference and handles only simple triads and selected sevenths. Unsupported extended chords raise errors rather than silently mislabeling.
- No Roman-function inference or process-aware intervention is implemented.
- `extensions` represent semitone intervals, not labels; e.g. dominant seventh = 10, major seventh = 11, ninth = 14. Added sixth = 9 in `add_intervals`.
- Altered fifth can be expressed by `omit_intervals=(7,), add_intervals=(6,)`; its symbolic name is not rendered yet.
- `inversion` is a simplified structural index and does not model every special classical 6/4 usage.

## Next research step

Build a separately testable intent constraint representation and a counterfactual optimizer that re-evaluates the **entire** harmonic path after intervention. Frozen EMH remains the reference baseline.
