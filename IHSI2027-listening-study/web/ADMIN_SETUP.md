# IHSI Listening Study — secure admin

## Firebase console
1. Authentication → Sign-in method → enable **Google** (not Anonymous). Choose a support email.
2. Authentication → Settings → Authorized domains: add `ihsi-listening-study.vercel.app` (and any preview domains used for admin). Google OAuth redirects/popup need authorized domains.
3. Project settings → General → Your apps → register a **Web app** if needed. Copy its **public web configuration** (not the private service account).
4. Firestore Security Rules: keep client reads and writes denied; admin data are read exclusively by the server API.

## Vercel environment variables (Production, and Preview if needed)
Existing secret: `FIREBASE_SERVICE_ACCOUNT_JSON` (private service-account JSON; never prefix with VITE_).
Add these **public** web-app config values:
- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_APP_ID`

These are public Firebase client identifiers; authorization is enforced **on the server**. The server accepts only verified Google sign-in with email `josef.pavlicek@gmail.com`. It verifies the Firebase ID token on every API request, including revoked tokens. For an extra defense-in-depth check, configure App Check or rate limits separately.

## Deploy
From the repository root, install this patch over `IHSI2027-listening-study/web/` and preserve `web/public/`. Run `npm install`, `npm run build`, stage only `IHSI2027-listening-study/web/`, review staged files and push. On Vercel redeploy after setting the variables.

## Usage
- `/` — public listening study, unchanged.
- `/admin` — Google login, view responses and expanded full JSON, download CSV.
- `/api/admin` — authenticated GET endpoint, pages of up to 100 records; server-side email allowlist.
- CSV is **UTF-8 with BOM**, CRLF line endings, 18 rating rows per complete participant, and RFC-style quoted cells. All pages are fetched before export.

**Do not distribute** the service-account JSON or put it in Git. `npm run dev` serves Vite only; use `vercel dev` for the API locally. The Google popup needs an allowed domain; production Vercel is the easiest place to test.
