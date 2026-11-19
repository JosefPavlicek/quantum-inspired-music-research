import React,{useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {initializeApp} from 'firebase/app';
import {getAuth,GoogleAuthProvider,onAuthStateChanged,signInWithPopup,signOut} from 'firebase/auth';
import './styles.css';
import './admin.css';

const owner='josef.pavlicek@gmail.com';
const fields=['participant_id','started_at','completed_at','received_at','language','preference','music_experience','age','completed','schema_version','clip_id','clip_sequence','blind_label','condition','naturalness','melody_fit','preference_match','play_seconds','audio_duration','max_position_seconds','played_fraction','timestamp'];
const csvValue=x=>'"'+String(x??'').replaceAll('"','""')+'"';
function downloadCSV(docs){
 const rows=docs.flatMap(d=>(d.responses||[]).map(r=>({...d,...r,participant_id:d.participant_id||d.id,received_at:d.received_at,responses:undefined,clip_order:undefined})));
 const content='\ufeff'+[fields.join(','),...rows.map(r=>fields.map(k=>csvValue(r[k])).join(','))].join('\r\n');
 const blob=new Blob([content],{type:'text/csv;charset=utf-8'});
 const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='ihsi2027_responses_'+new Date().toISOString().slice(0,10)+'.csv';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
const config={apiKey:import.meta.env.VITE_FIREBASE_API_KEY,authDomain:import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,projectId:import.meta.env.VITE_FIREBASE_PROJECT_ID,appId:import.meta.env.VITE_FIREBASE_APP_ID};
const configured=Object.values(config).every(Boolean);
const auth=configured?getAuth(initializeApp(config)):null;
function Admin(){
 const[user,setUser]=useState(null),[ready,setReady]=useState(false),[docs,setDocs]=useState([]),[cursor,setCursor]=useState(null),[loading,setLoading]=useState(false),[error,setError]=useState(''),[expanded,setExpanded]=useState({});
 useEffect(()=>{if(!auth){setReady(true);return;}return onAuthStateChanged(auth,u=>{setUser(u);setReady(true);setDocs([]);setCursor(null);setError('')});},[]);
 const allowed=user?.email?.toLowerCase()===owner&&user?.emailVerified;
 async function fetchPage(after=null,accumulate=false){
   if(!auth?.currentUser)return;setLoading(true);setError('');
   try{
     const token=await auth.currentUser.getIdToken();
     const response=await fetch('/api/admin'+(after?'?after='+encodeURIComponent(after):''),{headers:{Authorization:'Bearer '+token},cache:'no-store'});
     const data=await response.json();if(!response.ok)throw Error(data.error||'Unable to load');
     setDocs(prev=>accumulate?[...prev,...data.documents]:data.documents);setCursor(data.nextCursor);
   }catch(e){setError(e.message)}finally{setLoading(false)}
 }
 useEffect(()=>{if(allowed)fetchPage();},[allowed]);
 async function exportAll(){
   if(!auth?.currentUser)return;setLoading(true);setError('');
   try{
     let all=[],next=null;
     do{
       const token=await auth.currentUser.getIdToken();
       const response=await fetch('/api/admin'+(next?'?after='+encodeURIComponent(next):''),{headers:{Authorization:'Bearer '+token},cache:'no-store'});
       const data=await response.json();if(!response.ok)throw Error(data.error||'Export failed');
       all.push(...data.documents);next=data.nextCursor;
     }while(next);
     downloadCSV(all);
   }catch(e){setError(e.message)}finally{setLoading(false)}
 }
 return <div className="admin-shell"><header className="admin-top"><strong>IHSI · Research administration</strong><a href="/">← Listening study</a></header><main className="admin-main"><h1>Study responses</h1><p className="muted">Firestore · studies / IHSI2027 / responses</p>
 {!configured&&<p className="admin-alert">Firebase web configuration is missing. Set the four VITE_FIREBASE_* variables on Vercel.</p>}
 {!ready&&<p>Checking session…</p>}
 {ready&&!user&&configured&&<div className="admin-panel"><p>Sign in with the authorized Google account to view study results.</p><button className="btn primary" onClick={async()=>{setError('');try{await signInWithPopup(auth,new GoogleAuthProvider())}catch(e){setError(e.message)}}}>Sign in with Google</button></div>}
 {user&&!allowed&&<div className="admin-panel"><p className="admin-alert">This Google account is not authorized.</p><button className="btn secondary" onClick={()=>signOut(auth)}>Sign out</button></div>}
 {allowed&&<><div className="admin-toolbar"><span>Signed in: {user.email}</span><button className="btn secondary" onClick={()=>signOut(auth)}>Sign out</button><button className="btn secondary" disabled={loading} onClick={()=>fetchPage()}>Refresh</button><button className="btn primary" disabled={loading} onClick={exportAll}>{loading?'Loading…':'Download complete CSV (UTF-8)'}</button></div><div className="admin-panel"><p><strong>{docs.length}</strong> loaded respondents · <strong>{docs.reduce((n,d)=>n+(d.responses?.length||0),0)}</strong> ratings</p><div className="admin-scroll"><table className="admin-table"><thead><tr><th>Participant</th><th>Completed</th><th>Language</th><th>Preference</th><th>Music background</th><th>Ratings</th><th>Details</th></tr></thead><tbody>{docs.map(d=><React.Fragment key={d.id}><tr><td className="mono">{d.id}</td><td>{d.completed_at||'—'}</td><td>{d.language||'—'}</td><td>{d.preference||'—'}</td><td>{d.music_experience||'—'}</td><td>{d.responses?.length||0}</td><td><button className="admin-small" onClick={()=>setExpanded(s=>({...s,[d.id]:!s[d.id]}))}>{expanded[d.id]?'Close':'Open'}</button></td></tr>{expanded[d.id]&&<tr><td colSpan="7"><div className="admin-detail"><h3>Full record</h3><pre>{JSON.stringify(d,null,2)}</pre><h3>Individual ratings</h3><div className="admin-scroll"><table className="admin-table"><thead><tr>{['clip_sequence','clip_id','blind_label','condition','naturalness','melody_fit','preference_match','play_seconds','played_fraction'].map(k=><th key={k}>{k}</th>)}</tr></thead><tbody>{(d.responses||[]).map((r,i)=><tr key={i}>{['clip_sequence','clip_id','blind_label','condition','naturalness','melody_fit','preference_match','play_seconds','played_fraction'].map(k=><td key={k}>{String(r[k]??'')}</td>)}</tr>)}</tbody></table></div></div></td></tr>}</React.Fragment>)}</tbody></table></div>{cursor&&<button className="btn secondary" disabled={loading} onClick={()=>fetchPage(cursor,true)}>Load more</button>}</div></>}
 {error&&<p role="alert" className="admin-alert">{error}</p>}
 </main></div>;
}
createRoot(document.getElementById('root')).render(<Admin/>);
