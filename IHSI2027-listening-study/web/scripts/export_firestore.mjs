// Run locally with GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
// Never commit or upload the service-account file.
import {initializeApp,cert,getApps} from 'firebase-admin/app';
import {getFirestore} from 'firebase-admin/firestore';
import fs from 'node:fs';
const credentialPath=process.env.GOOGLE_APPLICATION_CREDENTIALS;
if(!credentialPath){console.error('Set GOOGLE_APPLICATION_CREDENTIALS to your local service-account JSON path');process.exit(1)}
const credentials=JSON.parse(fs.readFileSync(credentialPath,'utf8'));
if(!getApps().length)initializeApp({credential:cert(credentials)});
const snapshot=await getFirestore().collection('studies').doc('IHSI2027').collection('responses').get();
const records=snapshot.docs.map(doc=>({document_id:doc.id,...doc.data()}));
const timestamp=new Date().toISOString().replace(/[:.]/g,'-');
const jsonName=`ihsi2027_export_${timestamp}.json`;
const csvName=`ihsi2027_export_${timestamp}.csv`;
fs.writeFileSync(jsonName,JSON.stringify(records,null,2));
const fields=['document_id','participant_id','completed','started_at','completed_at','received_at','language','preference','music_experience','age','clip_id','clip_sequence','blind_label','condition','naturalness','melody_fit','preference_match','play_seconds','audio_duration','max_position_seconds','played_fraction','timestamp'];
const cell=x=>'"'+String(x??'').replaceAll('"','""')+'"';
const rows=records.flatMap(doc=>(doc.responses||[]).map(r=>({...doc,...r,responses:undefined})));
fs.writeFileSync(csvName,'\ufeff'+[fields.join(','),...rows.map(r=>fields.map(f=>cell(r[f])).join(','))].join('\r\n'));
console.log(`Exported ${records.length} participants, ${rows.length} ratings to ${jsonName} and ${csvName}`);
