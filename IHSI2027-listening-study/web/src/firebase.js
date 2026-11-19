import {initializeApp} from 'firebase/app';
import {getAuth,signInAnonymously} from 'firebase/auth';
import {getFirestore,doc,setDoc,serverTimestamp} from 'firebase/firestore';
const keys=['VITE_FIREBASE_API_KEY','VITE_FIREBASE_AUTH_DOMAIN','VITE_FIREBASE_PROJECT_ID','VITE_FIREBASE_APP_ID'];
export const configured=keys.every(k=>Boolean(import.meta.env[k]));
let db=null,auth=null;
if(configured){
  const app=initializeApp({apiKey:import.meta.env.VITE_FIREBASE_API_KEY,authDomain:import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,projectId:import.meta.env.VITE_FIREBASE_PROJECT_ID,appId:import.meta.env.VITE_FIREBASE_APP_ID});
  db=getFirestore(app);auth=getAuth(app);
}
export async function saveSession(session){
  if(!db||!auth)return false;
  const credential=auth.currentUser?{user:auth.currentUser}:await signInAnonymously(auth);
  const uid=credential.user.uid;
  await setDoc(doc(db,'ihsi2027_sessions',uid),{
    ...session,auth_uid:uid,updatedAt:serverTimestamp()
  });
  return true;
}
