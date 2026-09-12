import React from 'react';
import { Video, Search, Bell, ArrowRight, MapPin, ShieldCheck } from 'lucide-react';

export default function WorkspaceOverview({cameras,stats,health,onNavigate}) {
  const connected=cameras.filter(c=>c.connection_status==='CONNECTED');
  return <section className="workspace-overview"><div className="overview-intro"><p className="police-eyebrow">SENTINEL WORKSPACE</p><h1>What would you like to do?</h1><p>View your cameras, follow a vehicle, or review an alert.</p></div>
    <div className="overview-tasks">{[
      ['cameras','View cameras','Open connected feeds and inspect a camera.',Video,'Open cameras'],
      ['vehicle-trace','Find a vehicle','Search a registration and follow its saved observations.',Search,'Start a search'],
      ['live-alerts','Review alerts','Check confirmed watchlist matches and their evidence.',Bell,'Open alerts'],
    ].map(([id,title,description,Icon,action])=><button key={id} className="overview-task" onClick={()=>onNavigate(id)}><span className="task-icon"><Icon size={23}/></span><h2>{title}</h2><p>{description}</p><span className="task-action">{action}<ArrowRight size={17}/></span></button>)}</div>
    <section className="overview-network" aria-labelledby="network-heading"><div className="police-section-title"><h2 id="network-heading">Your workspace at a glance</h2><span className="police-muted">Current saved records</span></div><div className="overview-metrics">{[
      ['Registered cameras',stats?.cameras_registered,'gis'],['Connected now',connected.length,'cameras'],['Saved observations',stats?.total_sightings,'vehicle-trace'],['Open alerts',stats?.alerts_open,'live-alerts'],
    ].map(([label,value,target])=><button key={label} onClick={()=>onNavigate(target)}><strong>{value??'—'}</strong><span>{label}<ArrowRight size={14}/></span></button>)}</div></section>
    <div className="overview-lower"><section className="police-panel"><h2>Set up your workspace</h2><p className="police-muted">Keep camera details and vehicles of interest up to date.</p><button className="overview-row" onClick={()=>onNavigate('gis')}><MapPin size={19}/><span><strong>Camera registry & map</strong><small>Add sources, edit details and review coverage.</small></span><ArrowRight size={17}/></button><button className="overview-row" onClick={()=>onNavigate('watchlist')}><ShieldCheck size={19}/><span><strong>Manage the watchlist</strong><small>{stats?.watchlist_active ?? '—'} active entries. Add or import vehicles of interest.</small></span><ArrowRight size={17}/></button></section>
    <section className="police-panel"><h2>Before you investigate</h2><ol className="overview-guide"><li>Connect an authorized camera in <button onClick={()=>onNavigate('cameras')}>Live Cameras</button>.</li><li>Plate observations are saved after matching reads from separate frames.</li><li>Use <button onClick={()=>onNavigate('vehicle-trace')}>Find vehicle</button> to review where and when it was observed.</li></ol><p className="police-muted">Organizer replays and recorded footage stay labelled. No saved observation does not mean a vehicle was absent.</p>{health && !health.ai?.ready && <p className="overview-notice">Automatic recognition needs attention. <button onClick={()=>onNavigate('system-status')}>View system status</button></p>}</section></div>
  </section>;
}
