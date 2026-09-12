import React, { useState, useEffect, useRef, useCallback } from 'react';
import InvestigationWorkspace from './components/InvestigationWorkspace';
import WorkspaceOverview from './components/WorkspaceOverview';
import SessionGate from './components/SessionGate';
import { api } from './api';
import { pageFromHash } from './navigation';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import CommandCenterDashboard from './components/CommandCenterDashboard';
import LiveCamerasPage from './components/LiveCamerasPage';
import TrafficAnalyticsPage from './components/TrafficAnalyticsPage';
import IncidentCenterPage from './components/IncidentCenterPage';
import CameraManagementPage from './components/CameraManagementPage';
import AnprAssessmentPage from './components/AnprAssessmentPage';
import SystemStatusPage from './components/SystemStatusPage';
import DemoCamerasPage from './components/DemoCamerasPage';
import CameraFocusModal from './components/CameraFocusModal';

function CommandCenter({user}) {
  const [activeTab,setActiveTab]=useState(pageFromHash);
  const [collapsed,setCollapsed]=useState(false),[mobileOpen,setMobileOpen]=useState(false);
  const [health,setHealth]=useState(null),[stats,setStats]=useState(null),[cameras,setCameras]=useState([]);
  const [analyticsSummary,setAnalyticsSummary]=useState(null),[analyticsList,setAnalyticsList]=useState([]);
  const [eventsSummary,setEventsSummary]=useState(null),[eventsList,setEventsList]=useState([]);
  const [selectedCamera,setSelectedCamera]=useState(null),[loading,setLoading]=useState(true);
  const [isRefreshing,setIsRefreshing]=useState(false),[error,setError]=useState(null);
  const [systemState,setSystemState]=useState('LOADING');
  const fetching=useRef(false);
  const closeMobile=useCallback(()=>setMobileOpen(false),[]);
  const navigate=useCallback(id=>{window.location.hash=id;setActiveTab(id);setSelectedCamera(null);setMobileOpen(false);},[]);
  useEffect(()=>{const change=()=>{setActiveTab(pageFromHash());setSelectedCamera(null);setMobileOpen(false);};window.addEventListener('hashchange',change);return()=>window.removeEventListener('hashchange',change);},[]);
  useEffect(()=>{window.scrollTo({top:0,behavior:'instant'});},[activeTab]);
  const fetchAllData=useCallback(async(forceRefresh=false)=>{
    if(fetching.current)return;
    fetching.current=true;setIsRefreshing(true);
    try {
      const paths=['/api/system/health',`/api/cameras${forceRefresh?'?refresh=true':''}`,'/api/registry/stats','/api/analytics/summary','/api/analytics','/api/events/summary','/api/events'];
      const results=await Promise.allSettled(paths.map(path=>api(path,{timeout:forceRefresh?60000:8000})));
      const values=results.map(r=>r.status==='fulfilled'?r.value:null);
      setHealth(values[0]);setStats(values[2]);
      if(Array.isArray(values[1]))setCameras(values[1]);
      if(values[3])setAnalyticsSummary(values[3]);
      if(Array.isArray(values[4]))setAnalyticsList(values[4]);
      if(values[5])setEventsSummary(values[5]);
      if(Array.isArray(values[6]))setEventsList(values[6]);
      setSystemState(values[0]?'READY':'OFFLINE');
      if(forceRefresh && (results[1].status==='rejected'||values[0]?.catalogue_error))setError(values[0]?.catalogue_error||'Could not refresh the organizer catalogue. Try again.');
    } finally {fetching.current=false;setIsRefreshing(false);setLoading(false);}
  },[]);
  useEffect(()=>{let active=true,timer;async function poll(){await fetchAllData();if(active)timer=setTimeout(poll,5000);}poll();return()=>{active=false;clearTimeout(timer);};},[fetchAllData]);
  async function handleToggleConnection(id,connect) {
    try {setError(null);await api(`/api/cameras/${encodeURIComponent(id)}/${connect?'connect':'disconnect'}`,{method:'POST'});await fetchAllData();}
    catch(e){setError(e.message);}
  }
  const connectedCount=cameras.filter(c=>c.connection_status==='CONNECTED').length;
  const focused=selectedCamera?(cameras.find(c=>c.id===selectedCamera.id)||selectedCamera):null;
  return <div className="workspace-shell">
    <a className="skip-navigation" href="#workspace-content" onClick={e=>{e.preventDefault();document.getElementById('workspace-content')?.focus();}}>Skip to content</a>
    <Sidebar activeTab={activeTab} setActiveTab={navigate} onlineCamerasCount={connectedCount} alertCount={stats?.alerts_open} collapsed={collapsed} setCollapsed={setCollapsed} mobileOpen={mobileOpen} closeMobile={closeMobile}/>
    <div className="workspace-body"><Header activeTab={activeTab} totalCameras={cameras.length} connectedCount={connectedCount} onRefresh={()=>fetchAllData()} isRefreshing={isRefreshing} systemState={systemState} mobileOpen={mobileOpen} onOpenMenu={()=>setMobileOpen(true)}/>
      <main id="workspace-content" tabIndex={-1} className="workspace-content">
        {systemState==='OFFLINE'&&<div className="police-message error" role="alert">The local service is not responding. Displayed records may be out of date. Start the preview and use Refresh to reconnect.</div>}
        {error&&<div className="police-message error workspace-action-error" role="alert"><span>{error}</span><button onClick={()=>setError(null)} aria-label="Dismiss message">Dismiss</button></div>}
        {loading?<p className="workspace-loading" role="status">Opening your workspace…</p>:<>
          {activeTab==='home'&&<WorkspaceOverview cameras={cameras} stats={stats} health={health} onNavigate={navigate}/>}
          {['gis','vehicle-trace','watchlist','live-alerts'].includes(activeTab)&&<InvestigationWorkspace page={activeTab} user={user}/>}
          {activeTab==='dashboard'&&<CommandCenterDashboard cameras={cameras} analyticsSummary={analyticsSummary} eventsSummary={eventsSummary} onSelectCamera={setSelectedCamera} onNavigateToTab={navigate} streamMode="LIVE"/>}
          {activeTab==='cameras'&&<LiveCamerasPage cameras={cameras} onSelectCamera={setSelectedCamera} onToggleConnection={handleToggleConnection}/>}
          {activeTab==='analytics'&&<TrafficAnalyticsPage analyticsList={analyticsList} analyticsSummary={analyticsSummary}/>}
          {activeTab==='incidents'&&<IncidentCenterPage eventsList={eventsList} eventsSummary={eventsSummary}/>}
          {activeTab==='camera-management'&&<CameraManagementPage cameras={cameras} onToggleConnection={handleToggleConnection} onSelectCamera={setSelectedCamera} onRefresh={()=>fetchAllData(true)}/>}
          {activeTab==='anpr-assessment'&&<AnprAssessmentPage/>}
          {activeTab==='system-status'&&<SystemStatusPage health={health} totalCameras={cameras.length} connectedCount={connectedCount}/>}
          {activeTab==='demo'&&<DemoCamerasPage/>}
        </>}
      </main>
      <footer className="workspace-footer"><span>Sentinel · Gujarat</span><button onClick={()=>navigate('system-status')}>System details</button></footer>
    </div>
    {focused&&<CameraFocusModal camera={focused} analytics={analyticsList.find(a=>a.camera_id===focused.id)} onClose={()=>setSelectedCamera(null)} onToggleConnection={handleToggleConnection} streamMode="LIVE"/>}
  </div>;
}
export default function App(){return <SessionGate>{user=><CommandCenter user={user}/>}</SessionGate>;}
