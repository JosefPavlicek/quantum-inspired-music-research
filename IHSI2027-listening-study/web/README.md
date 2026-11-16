# IHSI 2027 – Listening Pilot (local, static)

Minimal Vite web application for a **pilot only**, with six excerpts, three blinded conditions, randomized clip and condition order, pre-listening preference elicitation, three 1–5 ratings per condition, and client-side CSV export.

## Audio layout

Copy the 18 files from `IHSI2027-listening-study/experiments/full_corpus/` into:

```
public/audio/clip_01/human_piano.wav
public/audio/clip_01/baseline_piano.wav
public/audio/clip_01/guided_piano.wav
...
public/audio/clip_06/human_piano.wav
public/audio/clip_06/baseline_piano.wav
public/audio/clip_06/guided_piano.wav
```

From the repository root, if this application is at `IHSI2027-listening-study/web/`:

```bash
for i in 01 02 03 04 05 06; do
  mkdir -p "IHSI2027-listening-study/web/public/audio/clip_$i"
  cp "IHSI2027-listening-study/experiments/full_corpus/clip_$i/"*_piano.wav "IHSI2027-listening-study/web/public/audio/clip_$i/"
done
cd IHSI2027-listening-study/web
npm install
npm run dev
```

Vite prints the development URL. For Vercel: root directory `IHSI2027-listening-study/web`, build command `npm run build`, output directory `dist`.

## Research caveats

- `GUIDED` uses a fixed 0.15 chord-change penalty; it is **not** individualized to the participant's selected preference. The `preference_match` question is subjective perceived match, not a verified causal intervention or true personalized intent preservation.
- All three stimuli should use identical piano instrument, tempo, and loudness. Audit alignment and final rendering before recruiting participants.
- The audio uses normalized pitch register and synthetic voicing; inspect these for scientific validity.
- HookTheory excerpt usage and public distribution rights must be reviewed before deployment. Do not publish audio to a public Vercel URL until permission/licensing is resolved.
- This app does not send data to a server. Each participant must export their CSV and provide it to the researcher. For a real distributed study, add secure backend collection, privacy information, and data handling controls.
- Preloading and WAV files may be heavy on mobile. Convert all three conditions to the **same** compressed audio codec/settings for public deployment, then update filenames in `src.js`.
- No formal inferential conclusions should be drawn from this six-excerpt convenience pilot alone.
