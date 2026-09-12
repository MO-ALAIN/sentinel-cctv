import React from 'react';
import { RefreshCw, Menu } from 'lucide-react';
import { navigation } from '../navigation';

export default function Header({activeTab,connectedCount,totalCameras,onRefresh,isRefreshing,systemState,mobileOpen,onOpenMenu}) {
  const page=navigation.find(p=>p.id===activeTab)||navigation[0];
  return <header className="workspace-header"><div className="workspace-breadcrumb"><button className="icon-button mobile-nav-open" aria-label="Open navigation" aria-expanded={mobileOpen} aria-controls="workspace-navigation" onClick={onOpenMenu}><Menu size={22}/></button><span>{page.group}</span><span aria-hidden="true">/</span><strong>{page.label}</strong></div><div className="workspace-header-actions"><span className={`connection-summary ${systemState==='OFFLINE'?'is-offline':''}`}><span className="status-dot"/>{systemState==='OFFLINE'?'Connection lost':systemState==='LOADING'?'Connecting…':`${connectedCount} of ${totalCameras} cameras connected`}</span><button className="icon-button" aria-label="Refresh workspace" title="Refresh workspace" onClick={onRefresh} disabled={isRefreshing}><RefreshCw size={17} className={isRefreshing?'animate-spin':''}/></button></div></header>;
}
