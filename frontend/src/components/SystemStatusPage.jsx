import React from 'react';
import { Activity, Cpu, Camera, Database, ShieldCheck } from 'lucide-react';

export default function SystemStatusPage({ totalCameras, connectedCount, health }) {
  const ai = health?.ai;
  const entries = [
    ['API service', !!health, health ? 'Responding' : 'Unavailable', Activity],
    ['Vehicle detector', !!ai?.ready, ai?.initialization_error || ai?.model_name || 'Not initialized', Cpu],
    ['OCR reader', !!ai?.anpr?.ready, ai?.anpr?.ready ? `${ai.anpr.ocr_engine || 'OCR'} loaded; accuracy requires validation` : 'OCR weights or dependencies unavailable', ShieldCheck],
    ['Camera feeds', connectedCount > 0, `${connectedCount} connected / ${totalCameras} registered`, Camera],
  ];
  return <div className="police-workspace">
    <div className="police-heading"><div><p className="police-eyebrow">RUNTIME HEALTH</p><h1>System status</h1><p>Actual service state and measured counters from this running process.</p></div><span className="police-badge">{health?.status || 'UNAVAILABLE'}</span></div>
    <div className="police-stats">{entries.map(([name, ready, detail, Icon])=><div key={name}><Icon/><span>{name}</span><strong style={{fontSize:18,color:ready?'#15704a':'#946515'}}>{ready?'Ready':'Unavailable'}</strong><p style={{gridColumn:'1 / 3',fontSize:12,color:'#64748b'}}>{detail}</p></div>)}</div>
    <div className="police-panel"><h2>Inference telemetry</h2><div className="police-table-wrap"><table><tbody>
      {[['Device',ai?.device_name || 'Unknown'],['CUDA available',ai?.cuda_available ? 'Yes':'No'],['Frames analyzed',ai?.total_frames_processed ?? 0],['Detections',ai?.total_detections_count ?? 0],['Last inference latency',`${ai?.last_latency_ms ?? 0} ms`],['Mean inference latency',`${ai?.average_latency_ms ?? 0} ms`],['Measured inference rate',`${ai?.inference_fps ?? 0} frames/s`],['Sampling interval',`Every ${ai?.frame_sampling_interval ?? '—'} frames`],['Tracker',ai?.tracker || 'Unknown']].map(([k,v])=><tr key={k}><th>{k}</th><td>{v}</td></tr>)}
    </tbody></table></div><p className="police-muted">Inference counters are not a complete multi-camera throughput or ANPR accuracy benchmark. Zero means no observations measured in this process.</p></div>
    <div className="police-panel"><h2>Deployment checks</h2><p className="police-muted">The current service uses local SQLite and file evidence. Network deployments require configured authentication, HTTPS, department-specific authorization, retention controls, backups and measured capacity. The registry audit is available to administrators.</p>{health?.catalogue_error && <p className="danger-text">{health.catalogue_error}</p>}</div>
  </div>;
}
