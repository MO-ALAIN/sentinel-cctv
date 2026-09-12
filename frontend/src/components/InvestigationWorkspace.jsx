import React, { useCallback, useEffect, useState } from 'react';
import { Search, MapPin, Bell, Shield, Plus, Download, RefreshCw, Upload, Check, Camera, X, FileText } from 'lucide-react';
import { api, apiUrl, normalizePlate, localTime, downloadReport } from '../api';
import GeoMap from './GeoMap';

const sources = ['LIVE', 'GOVERNMENT_REPLAY', 'RECORDED'];
const emptyCamera = { id: '', name: '', location: '', district: '', department: '', lat: '', lon: '', rtsp_url: '', source_type: 'LIVE', source_system: '', camera_type: 'IP', ownership: '', storage_details: '', retention_days: '', maintenance_status: 'UNKNOWN', geo_source: 'UNKNOWN', recording_started_at: '' };
const emptyWatch = { plate_number: '', reason: 'BOLO', severity: 'MEDIUM', description: '', source: 'MANUAL' };
const headings = {
  'vehicle-trace': ['Vehicle investigation', 'Find a registration across the camera network.'],
  'gis': ['Camera registry & GIS', 'Manage camera records, locations and coverage in one place.'],
  'watchlist': ['Vehicle watchlist', 'Manage representative or authorized records of vehicles of interest.'],
  'live-alerts': ['Watchlist alerts', 'Review confirmed registration matches and their observation evidence.'],
};
function Badge({ children, tone = '' }) { return <span className={`police-badge ${tone}`}>{children}</span>; }
function Empty({ children }) { return <div className="police-empty"><Search size={28} /><p>{children}</p></div>; }

export default function InvestigationWorkspace({ page, user }) {
  const [cameras, setCameras] = useState([]), [stats, setStats] = useState({}), [watchlist, setWatchlist] = useState([]), [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [loading, setLoading] = useState(true), [busy, setBusy] = useState(false);
  const [plate, setPlate] = useState(''), [trace, setTrace] = useState(null), [selected, setSelected] = useState(null);
  const [from, setFrom] = useState(''), [to, setTo] = useState(''), [source, setSource] = useState('');
  const [cameraForm, setCameraForm] = useState(null), [watchForm, setWatchForm] = useState(null);
  const [filter, setFilter] = useState(''), [department, setDepartment] = useState(''), [geo, setGeo] = useState(''), [status, setStatus] = useState('');
  const [registryView, setRegistryView] = useState('cameras'), [showRegistryMap, setShowRegistryMap] = useState(false), [cameraPage, setCameraPage] = useState(0);
  const [cameraType, setCameraType] = useState(''), [connection, setConnection] = useState('');
  const [surveys, setSurveys] = useState([]), [coverage, setCoverage] = useState(null);
  const [gaps, setGaps] = useState(null), [audit, setAudit] = useState(null), [showAcknowledged, setShowAcknowledged] = useState(false), [evidence, setEvidence] = useState(null);
  const admin = user?.role === 'admin', operator = admin || user?.role === 'operator';
  const load = useCallback(async () => {
    const paths = ['/api/registry/cameras', '/api/registry/stats', '/api/watchlist', `/api/alerts?${showAcknowledged ? '' : 'acknowledged=false&'}limit=200`];
    const results = await Promise.all(paths.map(path => api(path)));
    setCameras(results[0]); setStats(results[1]); setWatchlist(results[2]); setAlerts(results[3]);
  }, [showAcknowledged]);
  useEffect(() => {
    let active = true, timer;
    async function poll() {
      try { await load(); if (active) setError(''); } catch (e) { if (active) setError(e.message); }
      finally { if (active) { setLoading(false); timer = setTimeout(poll, 5000); } }
    }
    poll(); return () => { active = false; clearTimeout(timer); };
  }, [load]);
  useEffect(() => { setFilter(''); setNotice(''); setGaps(null); setAudit(null); }, [page]);

  async function action(fn, message) {
    setBusy(true); setError(''); setNotice('');
    try { await fn(); await load(); if (message) setNotice(message); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  function traceQuery() {
    const q = new URLSearchParams();
    if (from) q.set('from_time', new Date(from).toISOString());
    if (to) q.set('to_time', new Date(to).toISOString());
    if (source) q.set('source_type', source);
    return q;
  }
  async function search(event, value = plate) {
    event?.preventDefault(); const normalized = normalizePlate(value); setPlate(normalized);
    if (!normalized) { setError('Enter a registration number.'); return; }
    if (from && to && new Date(from) > new Date(to)) { setError('Start time must precede end time.'); return; }
    setTrace(null); setSelected(null);
    await action(async () => setTrace(await api(`/api/investigation/trace/${encodeURIComponent(normalized)}?${traceQuery()}`)));
  }
  async function saveCamera(event) {
    event.preventDefault(); const body = { ...cameraForm };
    for (const field of ['lat', 'lon', 'retention_days']) body[field] = body[field] === '' || body[field] == null ? null : Number(body[field]);
    body.recording_started_at = body.recording_started_at ? new Date(body.recording_started_at + 'Z').toISOString() : null;
    await action(async () => { await api('/api/registry/cameras', { method: 'POST', body: JSON.stringify(body) }); setCameraForm(null); }, 'Camera saved to the registry.');
  }
  async function importCSV(event, kind) {
    const file = event.target.files?.[0]; event.target.value = ''; if (!file) return;
    if (file.size > 2_000_000) { setError('CSV must be smaller than 2 MB.'); return; }
    await action(async () => { const result = await api(`/api/${kind}/import`, { method: 'POST', body: JSON.stringify({ csv: await file.text() }) }); setNotice(`${result.imported} records imported.`); });
  }
  async function loadCoverage() {
    const [survey, report] = await Promise.all([api('/api/registry/coverage'), api('/api/registry/coverage/gaps')]);
    setSurveys(survey.features); setCoverage(report);
  }
  async function importSurvey(event) {
    const file = event.target.files?.[0]; event.target.value = ''; if (!file) return;
    if (file.size > 2_000_000) { setError('Survey must be smaller than 2 MB.'); return; }
    await action(async () => {
      const body = JSON.parse(await file.text());
      await api('/api/registry/coverage', { method: 'POST', body: JSON.stringify(body) });
      await loadCoverage();
    }, 'Survey imported. Only verified geometry contributes to measured coverage.');
  }
  const visibleCameras = cameras.filter(c => `${c.id} ${c.name} ${c.location}`.toLowerCase().includes(filter.toLowerCase()) && (!department || c.department === department) && (!geo || c.geo_source === geo) && (!status || c.maintenance_status === status) && (!cameraType || c.camera_type === cameraType) && (!connection || c.connection_status === connection));
  const lastCameraPage = Math.max(0, Math.ceil(visibleCameras.length / 10) - 1);
  const currentCameraPage = Math.min(cameraPage, lastCameraPage);
  const pageCameras = visibleCameras.slice(currentCameraPage * 10, currentCameraPage * 10 + 10);
  const activeFilterCount = [department, geo, status, cameraType, connection].filter(Boolean).length;
  useEffect(() => setCameraPage(0), [filter, department, geo, status, cameraType, connection]);
  const visibleWatch = watchlist.filter(w => `${w.plate_number} ${w.description || ''}`.toLowerCase().includes(filter.toLowerCase()));
  const title = headings[page] || headings.gis;
  const cameraFields = [['id','Camera ID'], ['name','Camera name'], ['location','Location'], ['district','District'], ['department','Department'], ['source_system','Source system / vendor'], ['rtsp_url','Source URL or recording filename'], ['lat','Latitude'], ['lon','Longitude'], ['ownership','Owner'], ['storage_details','Storage / retention details'], ['retention_days','Retention days']];

  return <section className="police-workspace">
    <div className="police-heading"><div><h1>{title[0]}</h1><p>{title[1]}</p></div><button className="police-button secondary" disabled={busy} onClick={() => action(load)}><RefreshCw size={15} /> Refresh</button></div>
    {error && <div className="police-message error" role="alert">{error}</div>}{notice && <div className="police-message" role="status">{notice}</div>}
    {loading && <p className="police-muted">Loading saved records…</p>}

    {page === 'vehicle-trace' && <>
      <form className="police-panel" onSubmit={search}><div className="police-search"><Search size={20} /><input aria-label="Vehicle registration" placeholder="Enter registration, e.g. GJ01AB1234" value={plate} onChange={e => setPlate(e.target.value)} maxLength={30} /><button className="police-button" disabled={busy}>Find vehicle</button></div>
        <div className="police-filters"><label>From (your device time)<input type="datetime-local" value={from} onChange={e => setFrom(e.target.value)} /></label><label>To (your device time)<input type="datetime-local" value={to} onChange={e => setTo(e.target.value)} /></label><label>Video source<select value={source} onChange={e => setSource(e.target.value)}><option value="">All sources</option>{sources.map(s => <option key={s}>{s}</option>)}</select></label></div>
      </form>
      {!trace && !busy && <Empty>Search a plate to see its saved observations. Only observed camera locations appear in the history.</Empty>}
      {trace && <div className="police-panel"><div className="police-section-title"><div><h2>{trace.plate_number}</h2><p>{trace.total_sightings} observations • {trace.distinct_cameras} cameras • timestamps shown in IST</p></div><div className="police-actions">{trace.on_watchlist && <Badge tone="danger">{trace.watchlist.reason} • {trace.watchlist.severity}</Badge>}<button className="police-button secondary" onClick={() => action(() => downloadReport(`/api/investigation/export?plate=${encodeURIComponent(trace.plate_number)}&${traceQuery()}`, 'vehicle-history.csv'))}><Download size={15} /> Export history</button></div></div>
        {trace.route.length ? <><GeoMap route={trace.route} selectedId={selected?.id} onSelect={setSelected} /><div className="police-table-wrap"><table><thead><tr><th>Visit</th><th>Camera / location</th><th>Observed at (IST)</th><th>Recognition</th><th>Source</th><th>Evidence</th></tr></thead><tbody>{trace.route.map((r,i) => <tr key={r.id} className={selected?.id === r.id ? 'selected' : ''}><td><button className="police-link" onClick={() => setSelected(r)}>{i+1}</button></td><td><strong>{r.camera_id}</strong><small>{r.location || 'Unknown location'} • {r.geo_source}</small></td><td>{localTime(r.sighted_at)}<small>{r.timestamp_basis}</small></td><td><Badge tone={r.status === 'CONFIRMED' ? 'good' : 'warning'}>{r.status}</Badge><small>Score: {r.confidence == null ? '—' : `${Math.round(r.confidence*100)}%`}</small></td><td>{r.source_type}<small>{r.media_offset_seconds != null ? `Video +${r.media_offset_seconds.toFixed(1)}s` : 'No media offset'}</small></td><td>{r.crop_path ? <button className="police-link" onClick={() => setEvidence(r)}>View image</button> : 'Not saved'}</td></tr>)}</tbody></table></div></> : <Empty>No observations match these filters. This does not establish that the vehicle was absent from the area.</Empty>}
      </div>}
    </>}

    {page === 'gis' && <>
      <div className="workspace-tabs" role="group" aria-label="Registry sections">{[['cameras','Camera list & map'],['coverage','Coverage'],['tools','Imports & reports']].map(([id,label]) => <button key={id} aria-pressed={registryView===id} onClick={() => setRegistryView(id)}>{label}</button>)}</div>
      <div className="police-panel" hidden={registryView !== 'tools'}><h2>Imports & reports</h2><p className="police-muted">Bring in camera records, export your registry, and review metadata gaps or recent changes.</p><div className="police-actions">{admin && <><label className="police-button secondary"><Upload size={15} /> Import CSV<input type="file" accept=".csv,text/csv" hidden onChange={e => importCSV(e,'registry')} /></label></>}<button className="police-button secondary" onClick={() => action(() => downloadReport('/api/registry/export','camera-registry.csv'))}><Download size={15} /> Export</button><button className="police-button secondary" onClick={() => action(async () => setGaps(await api('/api/registry/gaps')))}><FileText size={15} /> Gap report</button>{admin && <button className="police-button secondary" onClick={() => action(async () => setAudit(await api('/api/registry/audit')))}>Audit history</button>}<button className="police-button secondary" onClick={() => action(async () => { await api('/api/cameras?refresh=true',{timeout:60000}); const h = await api('/api/system/health'); if(h.catalogue_error) throw new Error(h.catalogue_error); }, 'Organizer catalogue refreshed.')}>Import organizer catalogue</button></div></div>
      <div className="police-panel" hidden={registryView !== 'cameras'}><div className="registry-toolbar"><input aria-label="Filter cameras" placeholder="Search camera or location" value={filter} onChange={e => setFilter(e.target.value)} /><div className="police-actions"><button className="police-button secondary" aria-pressed={showRegistryMap} onClick={() => setShowRegistryMap(!showRegistryMap)}>{showRegistryMap?'Hide map':'Show map'}</button>{admin && <button className="police-button" onClick={() => setCameraForm({ ...emptyCamera })}><Plus size={15}/> Add camera</button>}</div></div><details className="registry-filters"><summary>Filters{activeFilterCount ? ` (${activeFilterCount} active)` : ''}</summary>
        <div className="police-filters"><select aria-label="Department filter" value={department} onChange={e => setDepartment(e.target.value)}><option value="">All departments</option>{[...new Set(cameras.map(c => c.department).filter(Boolean))].map(d => <option key={d}>{d}</option>)}</select><select aria-label="Coordinate filter" value={geo} onChange={e => setGeo(e.target.value)}><option value="">All coordinates</option>{['VERIFIED','REPRESENTATIVE','UNKNOWN'].map(d => <option key={d}>{d}</option>)}</select><select aria-label="Maintenance filter" value={status} onChange={e => setStatus(e.target.value)}><option value="">All maintenance states</option>{['CURRENT','DUE','FAULT','UNKNOWN'].map(d => <option key={d}>{d}</option>)}</select></div>
        <div className="police-filters"><select aria-label="Camera type filter" value={cameraType} onChange={e => setCameraType(e.target.value)}><option value="">All camera types</option>{['IP','ANALOG_DVR','VMS','FILE'].map(v => <option key={v}>{v}</option>)}</select><select aria-label="Connection filter" value={connection} onChange={e => setConnection(e.target.value)}><option value="">All connection states</option>{['CONNECTED','CONNECTING','DISCONNECTED','RECONNECTING','ERROR','ENDED','FRAME_DELIVERY_ERROR'].map(v => <option key={v}>{v}</option>)}</select></div>
        <button className="police-link" onClick={() => {setDepartment('');setGeo('');setStatus('');setCameraType('');setConnection('');}}>Clear filters</button></details>
        {showRegistryMap && <GeoMap cameras={visibleCameras} />}<p className="police-muted">{visibleCameras.length} cameras shown. {visibleCameras.filter(c => c.lat == null || c.lon == null).length} have no map coordinates. CSV columns follow the export format; source recordings must be in the configured media folder.</p>
        <div className="police-table-wrap"><table><thead><tr><th>Camera</th><th>Department / system</th><th>Location</th><th>Source / maintenance</th><th>Actions</th></tr></thead><tbody>{pageCameras.map(c => <tr key={c.id}><td><strong>{c.name}</strong><small>{c.id} • {c.camera_type}</small></td><td>{c.department || 'Unassigned'}<small>{c.source_system || 'Unspecified system'}</small></td><td>{c.location || 'Unknown'}<small>{c.geo_source}</small></td><td><Badge>{c.source_type}</Badge><small>{c.maintenance_status} / {c.connection_status}</small></td><td><div className="police-actions">{admin && <button className="police-link" onClick={() => setCameraForm({ ...emptyCamera, ...Object.fromEntries(Object.entries(c).filter(([k]) => k in emptyCamera)), rtsp_url: '', recording_started_at: c.recording_started_at ? new Date(c.recording_started_at).toISOString().slice(0,16) : '' })}>Edit</button>}{operator && <button className="police-link" onClick={() => action(() => api(`/api/cameras/${encodeURIComponent(c.id)}/connect`,{method:'POST'}),'Connection requested. Check Live Cameras for actual stream health.')}>Connect</button>}</div></td></tr>)}</tbody></table></div>
        {!!visibleCameras.length && <div className="registry-pagination"><span>{currentCameraPage*10+1}–{Math.min((currentCameraPage+1)*10,visibleCameras.length)} of {visibleCameras.length} cameras</span><div><button disabled={currentCameraPage===0} onClick={() => setCameraPage(currentCameraPage-1)}>Previous</button><button disabled={currentCameraPage===lastCameraPage} onClick={() => setCameraPage(currentCameraPage+1)}>Next</button></div></div>}
        {!!cameras.length && !visibleCameras.length && <Empty>No cameras match your search or filters. Clear filters or try a different camera name.</Empty>}
        {!cameras.length && <Empty>No cameras onboarded. Add an authorized source or import the organizer catalogue.</Empty>}
      </div>
      <div className="police-panel" hidden={registryView !== 'coverage'}><div className="police-section-title"><div><h2>Surveyed geographic coverage</h2><p>Compare a verified area boundary with surveyed camera footprints to locate uncovered ground.</p></div><div className="police-actions"><button className="police-button secondary" disabled={busy} onClick={() => action(loadCoverage)}>Measure coverage</button>{admin && <label className="police-button secondary"><Upload size={15} /> Import survey<input aria-label="Import survey GeoJSON" type="file" accept=".json,.geojson,application/json" hidden onChange={importSurvey} /></label>}</div></div>
        <details className="workspace-help"><summary>Survey file format & guidance</summary><p className="police-muted">Import GeoJSON polygons with properties id, name, kind (AREA or CAMERA), provenance (VERIFIED or REPRESENTATIVE), and camera_id for camera footprints. Mark geometry verified only after a survey or authoritative confirmation.</p></details>
        {coverage && <><p>{coverage.status === 'MISSING_VERIFIED_AREA' ? 'No verified survey boundary supplied. Geographic coverage cannot yet be measured.' : `${coverage.verified_camera_footprints} verified camera footprints · ${coverage.excluded_representative_features} representative features excluded.`}</p><p className="police-muted">{coverage.scope}</p><button className="police-link" onClick={() => action(() => downloadReport('/api/registry/coverage/gaps', 'geographic-coverage.json'))}>Download coverage report</button>
          <GeoMap surveys={surveys} uncovered={coverage.areas.filter(a => a.uncovered_geometry).map(a => ({ type:'Feature', properties:{name:a.name,kind:'GAP'}, geometry:a.uncovered_geometry }))} />
          {coverage.areas.map(a => <p key={a.area_id}><strong>{a.name}: {a.coverage_percent}% covered</strong> · {a.uncovered_m2.toLocaleString()} m² uncovered of {a.area_m2.toLocaleString()} m² surveyed</p>)}
          {admin && surveys.map(f => <p key={f.properties.id}>{f.properties.name} · {f.properties.kind} · {f.properties.provenance} <button className="police-link" onClick={() => action(async () => { await api(`/api/registry/coverage/${encodeURIComponent(f.properties.id)}`, {method:'DELETE'}); await loadCoverage(); }, 'Survey feature removed.')}>Remove survey feature</button></p>)}
        </>}
      </div>
      {registryView === 'tools' && gaps && <div className="police-panel"><h2>Registry gap report</h2><p className="police-muted">{gaps.scope}</p><button className="police-link" onClick={() => { const blob = new Blob([JSON.stringify(gaps,null,2)],{type:'application/json'}); const u=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=u;a.download='registry-gaps.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000); }}>Download report</button>{gaps.findings.length ? gaps.findings.map(g => <p key={g.camera_id} className="gap-row"><strong>{g.camera_id}</strong> {g.issues.join(' | ')}</p>) : <p>No gaps found by the available metadata checks.</p>}</div>}
      {registryView === 'tools' && audit && <div className="police-panel"><h2>Recent audit history</h2><div className="police-table-wrap"><table><thead><tr><th>Time (IST)</th><th>Actor</th><th>Action</th><th>Target</th></tr></thead><tbody>{audit.map(a => <tr key={a.id}><td>{localTime(a.created_at)}</td><td>{a.actor}</td><td>{a.action}</td><td>{a.target}</td></tr>)}</tbody></table></div></div>}
    </>}

    {page === 'watchlist' && <div className="police-panel"><div className="police-section-title"><input aria-label="Search watchlist" placeholder="Search plate or description" value={filter} onChange={e => setFilter(e.target.value)} />{admin && <div className="police-actions"><label className="police-button secondary"><Upload size={15} /> Import CSV<input type="file" accept=".csv,text/csv" hidden onChange={e => importCSV(e,'watchlist')} /></label><button className="police-button" onClick={() => setWatchForm({ ...emptyWatch })}><Plus size={15} /> Add vehicle</button></div>}</div><p className="police-muted">Source labels describe your supplied records. They do not establish a live VAHAN or police database connection. Matching begins with subsequent confirmed observations.</p><div className="police-table-wrap"><table><thead><tr><th>Registration</th><th>Reason</th><th>Severity</th><th>Description / source</th><th>Actions</th></tr></thead><tbody>{visibleWatch.map(w => <tr key={w.id}><td><strong>{w.plate_number}</strong></td><td>{w.reason}</td><td><Badge tone={w.severity === 'HIGH' ? 'danger' : ''}>{w.severity}</Badge></td><td>{w.description || '—'}<small>{w.source}</small></td><td>{admin && <div className="police-actions"><button className="police-link" onClick={() => setWatchForm(w)}>Edit</button><button className="police-link danger-text" onClick={() => action(() => api(`/api/watchlist/${w.id}`,{method:'DELETE'}),'Entry deactivated. It can be restored by adding the same plate.')}>Deactivate</button></div>}</td></tr>)}</tbody></table></div>{!visibleWatch.length && <Empty>No active watchlist entries. Add a representative record to test matching against actual recognized plates.</Empty>}</div>}

    {page === 'live-alerts' && <div className="police-panel"><div className="police-section-title"><h2>Latest matches</h2><label className="police-checkbox"><input type="checkbox" checked={showAcknowledged} onChange={e => setShowAcknowledged(e.target.checked)} /> Include acknowledged</label></div><p className="police-muted">Refreshes every five seconds. Recognition matches are leads for operator review. Recorded and organizer replay sources remain labelled.</p>{alerts.map(a => <article className="police-alert" key={a.id}><div className="alert-symbol"><Bell size={20} /></div><div className="alert-detail"><div className="police-actions"><h3>{a.plate_number}</h3><Badge tone={a.severity === 'HIGH' ? 'danger' : ''}>{a.severity}</Badge><Badge>{a.source_type || 'UNKNOWN'}</Badge></div><p>{a.message}</p><small>Observed {localTime(a.sighted_at)} IST • Alert {localTime(a.created_at)} IST • {a.camera_id}</small><div className="police-actions"><button className="police-link" onClick={() => setEvidence({id:a.sighting_id,plate_number:a.plate_number})}>Inspect evidence</button>{operator && !a.acknowledged && <button className="police-link" disabled={busy} onClick={() => action(() => api(`/api/alerts/${a.id}/acknowledge`,{method:'POST'}),'Alert acknowledged.')}><Check size={14} /> Acknowledge</button>}{!!a.acknowledged && <Badge tone="good">Acknowledged</Badge>}</div></div></article>)}{!alerts.length && <Empty>No matching alerts in this view. Alerts appear after a confirmed plate matches an active watchlist record.</Empty>}</div>}

    {cameraForm && <div className="police-overlay" role="dialog" aria-modal="true" aria-label="Camera onboarding"><form className="police-modal" onSubmit={saveCamera}><div className="police-section-title"><h2>Camera metadata</h2><button type="button" aria-label="Close camera form" onClick={() => setCameraForm(null)}><X /></button></div><div className="police-form-grid">{cameraFields.map(([key,label]) => <label key={key}>{label}<input required={['id','name'].includes(key)} value={cameraForm[key] ?? ''} onChange={e => setCameraForm({...cameraForm,[key]:e.target.value})} placeholder={key === 'rtsp_url' ? 'Blank preserves an existing source' : ''} /></label>)}{[['source_type','Source type',sources],['camera_type','Camera type',['IP','ANALOG_DVR','VMS','FILE']],['geo_source','Coordinate provenance',['UNKNOWN','VERIFIED','REPRESENTATIVE']],['maintenance_status','Maintenance',['UNKNOWN','CURRENT','DUE','FAULT']]].map(([key,label,options]) => <label key={key}>{label}<select value={cameraForm[key]} onChange={e => setCameraForm({...cameraForm,[key]:e.target.value})}>{options.map(o => <option key={o}>{o}</option>)}</select></label>)}<label>Recording start (UTC)<input type="datetime-local" value={cameraForm.recording_started_at} onChange={e => setCameraForm({...cameraForm,recording_started_at:e.target.value})} /></label></div><p className="police-muted">Saving stops an active feed; reconnect after editing. For recorded footage, supply its original start time to produce a source-time history. Coordinates must be marked verified or representative.</p><button className="police-button" disabled={busy}>Save camera</button>{error && <p className="danger-text" role="alert">{error}</p>}</form></div>}
    {watchForm && <div className="police-overlay" role="dialog" aria-modal="true" aria-label="Watchlist entry"><form className="police-modal narrow" onSubmit={e => {e.preventDefault();action(async () => {await api('/api/watchlist',{method:'POST',body:JSON.stringify({...watchForm,plate_number:normalizePlate(watchForm.plate_number)})});setWatchForm(null);},'Watchlist saved.');}}><div className="police-section-title"><h2>Vehicle of interest</h2><button type="button" aria-label="Close watchlist form" onClick={() => setWatchForm(null)}><X /></button></div><label>Registration<input required value={watchForm.plate_number} onChange={e => setWatchForm({...watchForm,plate_number:e.target.value})} /></label><label>Reason<select value={watchForm.reason} onChange={e => setWatchForm({...watchForm,reason:e.target.value})}>{['BOLO','STOLEN','WANTED','SUSPECT','MISSING'].map(v => <option key={v}>{v}</option>)}</select></label><label>Severity<select value={watchForm.severity} onChange={e => setWatchForm({...watchForm,severity:e.target.value})}>{['LOW','MEDIUM','HIGH'].map(v => <option key={v}>{v}</option>)}</select></label><label>Description<textarea value={watchForm.description || ''} onChange={e => setWatchForm({...watchForm,description:e.target.value})} /></label><label>Record source<input value={watchForm.source} onChange={e => setWatchForm({...watchForm,source:e.target.value})} /></label><button className="police-button" disabled={busy}>Save entry</button>{error && <p className="danger-text" role="alert">{error}</p>}</form></div>}
    {evidence && <div className="police-overlay" role="dialog" aria-modal="true" aria-label="Observation evidence"><div className="police-modal narrow"><div className="police-section-title"><h2>{evidence.plate_number} • Evidence</h2><button aria-label="Close evidence" onClick={() => setEvidence(null)}><X /></button></div><img className="evidence-image" src={apiUrl(`/api/investigation/evidence/${evidence.id}`)} alt="Saved registration plate crop" onError={e => { e.currentTarget.style.display='none'; }} /><p>Observation #{evidence.id}. If the image is unavailable, the file was not saved or is no longer present. Review original footage before acting on a match.</p></div></div>}
  </section>;
}
