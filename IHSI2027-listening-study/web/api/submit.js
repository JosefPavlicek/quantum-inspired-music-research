import { initializeApp, cert, getApps } from 'firebase-admin/app';
import { getFirestore, FieldValue } from 'firebase-admin/firestore';

function database() {
  const raw = process.env.FIREBASE_SERVICE_ACCOUNT_JSON;
  if (!raw) throw new Error('Server Firebase credentials not configured');
  if (!getApps().length) initializeApp({ credential: cert(JSON.parse(raw)) });
  return getFirestore();
}

const allowedConditions = ['human', 'baseline', 'guided'];
const allowedPreferences = ['stable', 'dynamic', 'neutral'];
const allowedExperience = ['none', 'informal', 'basic', 'advanced', 'skip'];
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const score = x => Number.isInteger(x) && x >= 1 && x <= 5;
const finite = x => typeof x === 'number' && Number.isFinite(x) && x >= 0 && x <= 3600;
const iso = x => typeof x === 'string' && !Number.isNaN(Date.parse(x)) && x.length < 40;
function validate(s) {
  if (!s || typeof s !== 'object' || Array.isArray(s) || !uuid.test(s.participant_id || '')) return false;
  if (!iso(s.started_at) || !iso(s.completed_at) || s.completed !== true) return false;
  if (!['cs', 'en'].includes(s.language) || !allowedPreferences.includes(s.preference)) return false;
  if (s.music_experience != null && !allowedExperience.includes(s.music_experience)) return false;
  if (s.age != null && (!Number.isInteger(s.age) || s.age < 18 || s.age > 70)) return false;
  if (!Array.isArray(s.responses) || s.responses.length !== 18 || !Array.isArray(s.clip_order) || s.clip_order.length !== 6) return false;
  const seen = new Set();
  const clips = new Set();
  for (const r of s.responses) {
    if (!r || typeof r !== 'object' || r.participant_id !== s.participant_id || r.started_at !== s.started_at) return false;
    if (typeof r.clip_id !== 'string' || !/^[a-zA-Z0-9_-]{1,60}$/.test(r.clip_id)) return false;
    if (!Number.isInteger(r.clip_sequence) || r.clip_sequence < 1 || r.clip_sequence > 6) return false;
    if (!['A', 'B', 'C'].includes(r.blind_label) || !allowedConditions.includes(r.condition) || r.preference !== s.preference) return false;
    if (!score(r.naturalness) || !score(r.melody_fit) || !score(r.preference_match)) return false;
    if (!finite(r.play_seconds) || r.play_seconds < 1 || !finite(r.audio_duration) || !finite(r.max_position_seconds)) return false;
    if (typeof r.played_fraction !== 'number' || !Number.isFinite(r.played_fraction) || r.played_fraction < 0 || r.played_fraction > 1) return false;
    const key = `${r.clip_id}:${r.condition}`;
    if (seen.has(key)) return false;
    seen.add(key); clips.add(r.clip_id);
  }
  if (clips.size !== 6) return false;
  for (let i=0; i<6; i++) {
    const o=s.clip_order[i];
    if (!o || typeof o.clip_id !== 'string' || !Array.isArray(o.conditions) || o.conditions.length !== 3 || new Set(o.conditions).size !== 3 || !o.conditions.every(c=>allowedConditions.includes(c))) return false;
    for (let j=0;j<3;j++) if (!s.responses.some(r=>r.clip_id===o.clip_id && r.clip_sequence===i+1 && r.condition===o.conditions[j] && r.blind_label==='ABC'[j])) return false;
  }
  return true;
}

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST') { res.setHeader('Allow', 'POST'); return res.status(405).json({error:'Method not allowed'}); }
  const length = Number(req.headers['content-length'] || 0);
  if (length > 100_000) return res.status(413).json({error:'Payload too large'});
  if (!validate(req.body)) return res.status(400).json({error:'Invalid study submission'});
  try {
    const doc = database().collection('studies').doc('IHSI2027').collection('responses').doc(req.body.participant_id);
    // Idempotent retries: never overwrite a previous submission.
    await doc.create({ ...req.body, received_at: FieldValue.serverTimestamp(), schema_version: 1 });
    return res.status(201).json({ok:true});
  } catch (err) {
    if (err.code === 6 || err.code === 'already-exists') return res.status(200).json({ok:true, duplicate:true});
    console.error('IHSI submission failed:', err.message);
    return res.status(503).json({error:'Storage temporarily unavailable'});
  }
}
