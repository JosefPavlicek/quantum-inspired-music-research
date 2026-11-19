# IHSI 2027 — Vercel + Firestore deployment

**Never commit or share the service-account JSON.** Use the service account you downloaded from Firebase Console. Keep Firestore client security rules locked (`allow read, write: if false;`). Firebase Admin SDK on the server bypasses client rules.

## 1. Vercel project

Create a Vercel project from the Git repository. **Root Directory** must be `IHSI2027-listening-study/web` (not repository root). Framework: Vite; build `npm run build`; output `dist`.

## 2. Secret environment variable

Vercel → Project → Settings → Environment Variables:

- Name: `FIREBASE_SERVICE_ACCOUNT_JSON`
- Value: **the complete, single-line JSON contents** of your Firebase service-account file (JSON can contain escaped `\n` within the `private_key` string). Do not paste into chat or Git.
- Environments: Production and Preview (if needed).

For Codespaces testing, create `web/.env.local` manually with `FIREBASE_SERVICE_ACCOUNT_JSON=` followed by the JSON on one line. Never commit it. If the CLI does not load it, run `vercel env pull .env.local` after configuring the variable in Vercel.

## 3. Install and run

```bash
cd IHSI2027-listening-study/web
npm install
npx vercel login
npx vercel link
npx vercel dev
```

Use the port shown by `vercel dev`, normally 3000. `npm run dev` launches Vite only; `/api/submit` will not work there.

## 4. Test

Complete one test response. Verify `studies/IHSI2027/responses/<participant_id>` in Firebase Console. If submission fails, the UI allows retry and CSV export. A retry uses the same participant ID, so it does not create a duplicate.

## 5. Deploy

Commit only reviewed source and configuration files; exclude WAV/corpus assets if their license prohibits public distribution. `npx vercel --prod` deploys the linked project. Confirm `/corpus.json` and all 18 WAV URLs work, and perform a full test before sending to students.

## Security and ethics

- No Firebase admin credentials in `VITE_*` variables or browser code.
- The public API accepts anonymous submissions. It validates format, length, and uniqueness, but **cannot guarantee human-only submissions or enforce a genuine listen**. Before public distribution, add Vercel firewall/rate limiting or CAPTCHA/Turnstile if abuse is a concern.
- Participants can save a CSV backup. The app does not retain unfinished responses across a page reload.
- Consent text should accurately disclose storage and retention; verify permission to distribute HookTheory-derived audio clips.
