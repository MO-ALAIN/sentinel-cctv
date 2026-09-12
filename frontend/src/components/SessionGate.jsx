import React, { useEffect, useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { api } from '../api';

export default function SessionGate({ children }) {
  const [session, setSession] = useState(null), [error, setError] = useState('');
  const [username, setUsername] = useState('operator'), [password, setPassword] = useState(''), [busy, setBusy] = useState(false);
  async function refresh() { try { setSession(await api('/api/auth/session')); setError(''); } catch (e) { setError(e.message); } }
  useEffect(() => { refresh(); }, []);
  if (session?.user) return <><div className="session-strip"><span><ShieldCheck size={14} /> {session.mode === 'LOCAL_ONLY' ? 'Local preview · accessible on this computer' : `Signed in as ${session.user.name}`}</span>{session.authentication_configured && <button onClick={async () => { await api('/api/auth/logout',{method:'POST'}); setSession(null); refresh(); }}>Sign out</button>}</div>{children(session.user)}</>;
  return <div className="session-screen"><form className="police-modal narrow" onSubmit={async e => { e.preventDefault(); setBusy(true); try { await api('/api/auth/login',{method:'POST',body:JSON.stringify({username,password})}); setPassword(''); await refresh(); } catch(e) {setError(e.message);} finally {setBusy(false);} }}><ShieldCheck size={38} color="#1976d2" /><p className="police-eyebrow">SENTINEL • GUJARAT</p><h1>Command center access</h1>{session ? <><label>Role<select value={username} onChange={e=>setUsername(e.target.value)}><option>operator</option><option>admin</option><option>viewer</option></select></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required /></label><button className="police-button" disabled={busy}>Sign in</button></> : <p>Connecting to the command center…</p>}{error && <><p className="danger-text" role="alert">{error}</p><button className="police-button secondary" type="button" onClick={refresh}>Retry connection</button></>}</form></div>;
}
