# IHSI 2027 — HARMONIX Listening Study

A reproducible listening-study subproject within the [`quantum-inspired-music-research`](https://github.com/JosefPavlicek/quantum-inspired-music-research) repository.

**Live study:** https://ihsi-listening-study.vercel.app/

**Research focus:** *When Good Harmony Is Not Enough: Preserving Human Intention in Explainable Music Generation* (IHSI 2027).

## Study overview

The study investigates how listeners perceive different harmonizations of the same melody, with particular attention to musical naturalness, melody–harmony compatibility, and alignment with a listener's stated preference for harmonic stability or variation.

The current study contains **six musical excerpts**. Each excerpt is presented in three conditions, using consistent piano rendering:

- **HUMAN:** harmony from the source annotation.
- **BASELINE:** harmonization produced by the corrected Explainable Melody Harmonizer (EMH) pipeline integrated into HARMONIX.
- **GUIDED:** a structurally guided corrected-EMH harmonization using a fixed harmonic-persistence/chord-change penalty of **0.15**.

The guided condition is a fixed experimental treatment; it is **not** adapted to each participant's stated preference. The three conditions are presented under blinded labels, and the survey records the presentation order.

Participants listen to the excerpts and evaluate each condition on three five-point scales: perceived naturalness, fit of harmony to melody, and fit to their initially stated preference. The study is available in Czech and English and is designed primarily for phones and tablets.

## Live application and administration

- **Participant survey:** https://ihsi-listening-study.vercel.app/
- **Research administration:** https://ihsi-listening-study.vercel.app/admin
- **Frontend:** React + Vite (`web/`)
- **Deployment:** Vercel
- **Storage:** Cloud Firestore, under `studies/IHSI2027/responses`
- **Admin authentication:** Google sign-in; server-side access checks are required for protected data export

The survey collects anonymous response identifiers, consent, experimental ratings, condition labels and order, timing/playback metrics, and optional demographic information. Responses are submitted to the server-side API and stored in Firestore. The admin interface supports inspecting responses and exporting a UTF-8 CSV suitable for downstream analysis.

**Data collection behavior:** The deployed study submits responses at completion, rather than saving each excerpt independently. Participants who leave early may therefore not have a persisted response.

## Repository structure

```text
IHSI2027-listening-study/
├── README.md                  # This document
├── scripts/                   # Corpus preparation, harmonization and audio rendering
├── experiments/full_corpus/   # Per-excerpt research artifacts and metadata
├── public/                    # Research prototype assets (review before publishing)
└── web/
    ├── src/                  # React survey and admin interface
    ├── api/                  # Vercel serverless API
    ├── public/               # Published corpus manifest and approved audio assets
    ├── scripts/              # Data export utilities
    ├── FIREBASE_SETUP.md
    ├── ADMIN_SETUP.md
    └── DEPLOY_VERCEL.md
```

Some directories may contain generated or third-party material that must not be committed or redistributed without an appropriate license. Refer to the actual repository tree for the precise files in each directory.

## Running the web app locally

From the repository root:

```bash
cd IHSI2027-listening-study/web
npm ci
npm run dev -- --host 0.0.0.0
```

To verify a production build:

```bash
npm run build
```

The frontend reads the published `web/public/corpus.json` manifest and associated audio files. The server-side submission and administration endpoints are intended for Vercel deployment; running Vite locally does not automatically reproduce the Vercel serverless runtime.

For deployment, Firebase configuration, administrator access, and CSV export, see the documentation in `web/`. Never commit `.env.local`, service-account JSON, API tokens, or private keys.

## Research pipeline and reproducibility

The `scripts/` directory contains utilities for preparing the corpus, generating baseline and guided harmonizations, and rendering audio. The experiment directories retain per-excerpt artifacts needed to audit the relationship between source material and generated variants.

An earlier standalone technical audio pilot can be generated with:

```bash
python scripts/export_audio.py --dataset data/Hooktheory.json.gz --output public/audio/pilot_reference.wav
```

The HookTheory source dataset is **not distributed** with this repository. Supply a locally obtained, appropriately licensed copy at `data/Hooktheory.json.gz` when using this legacy pilot command. This command does **not** reproduce all six three-condition study excerpts; use the current corpus-generation scripts and documented experimental configuration for the full study.

For a reproducible publication, retain and document the precise source-record identifiers, model/version provenance, generation parameters, audio-rendering settings, and any exclusions or manual corrections. Avoid implying that a build of the web app alone regenerates the research corpus.

## Study data and analysis

The Firestore response collection is:

```text
studies / IHSI2027 / responses / <anonymous-participant-id>
```

Each completed response contains participant-level metadata and per-condition evaluations, including playback metrics. The admin CSV export is intended as the primary analysis input. Test submissions must be marked or excluded before reporting study results. Do not commit raw participant exports to a public repository; publish only appropriately anonymized and ethically cleared derived data.

## Licensing, ethics, and data safety

- HookTheory annotations and any third-party musical material remain subject to their respective owners' rights and licensing conditions. Do not commit the complete HookTheory dataset or redistribute derived audio unless permission or another valid legal basis has been established.
- Keep service-account credentials and all other secrets out of Git. Firebase client configuration is public by design; privileged service-account credentials are not.
- Restrict administrative reads and exports to authorized accounts on the server, not only in the browser UI.
- Do not publish personally identifying respondent information. Obtain appropriate consent and follow institutional research and data-retention requirements.
- The live study is a research instrument; reported findings require actual participant data, quality checks, and statistical analysis. No listener-preference outcome is presumed by the software implementation.

## Status

The bilingual, mobile-first listening survey, Vercel submission API, Firestore persistence, Google-authenticated administration, and CSV export have been deployed and smoke-tested. The study is ready for a final distribution and rights/ethics check before wider participant recruitment.
