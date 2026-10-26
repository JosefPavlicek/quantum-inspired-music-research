# HARMONIX v0.9.0 — Independent knowledge-guided candidate vocabulary

## Scope
This is a **candidate generator only**, not a harmonizer integration, coverage experiment, or intervention result. The baseline remains the frozen EMH generator. This patch adds no changes to original EMH, `vendor/emh_baseline`, or existing HARMONIX code.

- `baseline`: run the original frozen generator; no proxy is offered by this module.
- `corrected`: 7 triads and 3 selected sevenths, with correct V7 and a major V/V7 in minor.
- `extended`: corrected plus four additional diatonic seventh types and five secondary dominant sevenths, 19 labeled candidates total.

The current model uses pitch-class sets and simple canonical spellings. It does not model inversions, voicings, modulation, enharmonic functional spelling, voice leading, or verify secondary-dominant resolutions. Secondary dominants are **candidate options**, not forced progressions. The corrected model uses the raised leading tone in the minor dominant but retains other natural-minor triads. In major the vii seventh is half-diminished; in minor the VII seventh is a natural-minor dominant seventh. These are explicitly chosen simplified conventions, not a full theory engine.

## Validation
Run `python -m pytest tests/ -q` from HARMONIX.

## Research firewall
The uploaded vocabulary audit used TEST material. Any choices motivated by it are exploratory and cannot justify an unbiased final TEST claim. Define independent development data and a genuinely untouched holdout before tuning. Do not use reference annotations for candidate generation or intervention ranking. Frozen model and historical results remain unchanged.

## Next checkpoint
Integrate separately into HARMONIX optimization and evaluate coverage independently of post-hoc agreement. This patch is only a generator.
