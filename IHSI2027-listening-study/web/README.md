# IHSI 2027 listening study — mobile-first React UI

Replace the **web** folder's `src.js`, `index.html`, and `package.json` with the files from this package; add `src/`, `src/firebase.js`, `src/styles.css`, `.env.example`, and `.gitignore`. Keep the existing `web/public/corpus.json` and `web/public/audio/` untouched. The old `src.js` is no longer used.

```bash
cd IHSI2027-listening-study/web
npm install
npm run dev
```

## Firebase

Copy `.env.example` to `.env.local` and fill the four values from **Firebase Console → Project settings → Your apps → Web app**. Never put service-account private keys in client code. Enable Cloud Firestore. The application writes one document per completed participant to `ihsi2027_sessions/{participant_id}`. Without Firebase configuration it allows local CSV export **for testing only**; do not send the public study link until remote saving and security rules are verified.

**Security:** Anonymous UUIDs are not authorization. Do not use unrestricted Firestore `allow write: if true` for a public deployment. Recommended production setup: Firebase Anonymous Auth with rules restricting each participant to their own document, strict schema validation, App Check and rate limits; alternatively use a server-side validated submission endpoint. The current implementation intentionally does not claim to provide secure public writes without these controls.

## Data collection

Three blinded conditions are randomized within each of six shuffled excerpts. All ratings must be answered and playback must have started for all three variants before proceeding. The UI does **not** require complete playback. It records cumulative play time, maximum playhead position, duration and fraction reached. `started_at` and `completed_at` are ISO timestamps. The final demographic questions are optional. Avoid using these metrics as evidence that someone actually listened attentively; they only record player interaction.

The study saves after completion. For resilience against interruptions, implement periodic saving after Firebase Auth/security configuration is in place. Confirm music/audio licensing before distributing HookTheory-derived clips publicly. Do not commit `.env.local`, credentials or personally identifying response data.
