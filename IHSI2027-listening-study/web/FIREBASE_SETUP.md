# IHSI 2027 – Firebase setup

1. Firebase console → choose your project → Build → Authentication → Sign-in method → enable **Anonymous**.
2. Build → Firestore Database → Create database (if needed). Select a suitable EU location before creation.
3. Firestore → Rules → replace with `firestore.rules` from this package and Publish. **Warning:** if this is a shared Firebase project, replacing all rules could break other apps. Instead merge only the `match /ihsi2027_sessions/{uid}` block into existing rules and preserve all existing rules.
4. Project settings → General → Your apps → Web app → Firebase SDK setup/config. Copy `apiKey`, `authDomain`, `projectId`, `appId` into `web/.env.local` (use `.env.example` as template). These are web app config values, NOT a service account key.
5. Restart Vite (`npm run dev`). Complete a test survey and verify one document in Firestore collection `ihsi2027_sessions`. Test the exported CSV too.
6. Firestore rules block participants from reading others' responses; administrators can export through Firebase Console. Anonymous authentication does not prevent scripted abuse; configure App Check and monitoring before public distribution.

Do not commit `.env.local`, service-account credentials, or respondent data. Check audio licensing before publishing recordings.
