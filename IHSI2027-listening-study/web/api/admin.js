import { initializeApp, cert, getApps } from 'firebase-admin/app';
import { getAuth } from 'firebase-admin/auth';
import { getFirestore } from 'firebase-admin/firestore';

const OWNER_EMAIL = 'josef.pavlicek@gmail.com';
function setup() {
  if (!getApps().length) {
    const raw = process.env.FIREBASE_SERVICE_ACCOUNT_JSON;
    if (!raw) throw new Error('Firebase service account not configured');
    initializeApp({ credential: cert(JSON.parse(raw)) });
  }
}
export default async function handler(req,res) {
  res.setHeader('Cache-Control','private, no-store, max-age=0');
  res.setHeader('X-Content-Type-Options','nosniff');
  if (req.method !== 'GET') {res.setHeader('Allow','GET');return res.status(405).json({error:'Method not allowed'});}
  try {
    setup();
    const match = /^Bearer (\S+)$/.exec(req.headers.authorization || '');
    if (!match) return res.status(401).json({error:'Sign in required'});
    const user = await getAuth().verifyIdToken(match[1],true);
    if (!user.email_verified || user.email?.toLowerCase() !== OWNER_EMAIL || user.firebase?.sign_in_provider !== 'google.com') {
      return res.status(403).json({error:'Access denied'});
    }
    const ref = getFirestore().collection('studies').doc('IHSI2027').collection('responses');
    const limit = 100;
    let query = ref.orderBy('__name__').limit(limit);
    if (typeof req.query.after === 'string' && req.query.after.length < 150 && /^[a-zA-Z0-9_-]+$/.test(req.query.after)) {
      query = query.startAfter(req.query.after);
    } else if (req.query.after) return res.status(400).json({error:'Invalid cursor'});
    const snapshot = await query.get();
    const documents = snapshot.docs.map(d => ({id:d.id,...d.data(),received_at:d.get('received_at')?.toDate?.()?.toISOString?.() || null}));
    return res.status(200).json({documents,nextCursor:snapshot.size===limit?snapshot.docs[snapshot.docs.length-1].id:null});
  } catch(err) {
    if (err.code?.startsWith?.('auth/')) return res.status(401).json({error:'Invalid or expired session'});
    console.error('Admin read failed:',err.message);
    return res.status(500).json({error:'Unable to load study data'});
  }
}
