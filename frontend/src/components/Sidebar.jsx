import React, { useEffect, useRef, useState } from 'react';
import { ShieldCheck, ChevronLeft, ChevronRight, ChevronDown, X, Sliders } from 'lucide-react';
import { navigation } from '../navigation';

export default function Sidebar({ activeTab, setActiveTab, onlineCamerasCount, alertCount, collapsed, setCollapsed, mobileOpen, closeMobile }) {
  const [moreOpen,setMoreOpen]=useState(false);
  const panel=useRef(null);
  const advanced=navigation.find(p=>p.id===activeTab)?.group==='More tools';
  useEffect(()=>{ if(advanced) setMoreOpen(true); },[activeTab,advanced]);
  useEffect(()=>{
    if(!mobileOpen) return;
    const previous=document.activeElement;
    panel.current?.querySelector('button')?.focus();
    function key(event) {
      if(event.key==='Escape') closeMobile();
      if(event.key==='Tab') {
        const elements=[...panel.current.querySelectorAll('button')].filter(e=>e.getClientRects().length && !e.disabled);
        const first=elements[0],last=elements.at(-1);
        if(event.shiftKey && document.activeElement===first) { event.preventDefault();last?.focus(); }
        else if(!event.shiftKey && document.activeElement===last) {event.preventDefault();first?.focus();}
      }
    }
    document.addEventListener('keydown',key);
    return ()=>{document.removeEventListener('keydown',key);previous?.focus();};
  },[mobileOpen,closeMobile]);
  function item(p) {
    const Icon=p.icon, active=activeTab===p.id;
    const count=p.id==='cameras'?onlineCamerasCount:p.id==='live-alerts'?alertCount:null;
    return <button key={p.id} aria-label={p.label} title={collapsed?p.label:undefined} aria-current={active?'page':undefined}
      className={`workspace-nav-item ${active?'is-active':''}`} onClick={()=>{setActiveTab(p.id);closeMobile();}}>
      <Icon size={19}/><span className="nav-label">{p.label}</span>{count>0 && <span className="nav-count">{count}</span>}
    </button>;
  }
  return <>
    {mobileOpen && <button className="navigation-backdrop" aria-label="Close navigation" onClick={closeMobile}/>}
    <aside ref={panel} id="workspace-navigation" role={mobileOpen?'dialog':undefined} aria-modal={mobileOpen?true:undefined} aria-label={mobileOpen?'Navigation':undefined} className={`workspace-sidebar ${collapsed?'is-collapsed':''} ${mobileOpen?'is-mobile-open':''}`}>
      <div className="workspace-brand"><ShieldCheck size={27}/><div className="brand-copy"><strong>Sentinel</strong><span>Camera & investigation workspace</span></div><button className="mobile-nav-close icon-button" aria-label="Close navigation" onClick={closeMobile}><X size={20}/></button></div>
      <nav aria-label="Main navigation"><p className="nav-section-label">Workspace</p>{navigation.filter(p=>p.group==='Workspace').map(item)}
        <button className="workspace-nav-item more-tools-toggle" aria-expanded={moreOpen} aria-controls="more-tools" title="More tools" onClick={()=>setMoreOpen(!moreOpen)}><Sliders size={19}/><span className="nav-label">More tools</span><ChevronDown size={15} className={moreOpen?'rotate-180':''}/></button>
        <div id="more-tools" hidden={!moreOpen}>{navigation.filter(p=>p.group==='More tools').map(item)}</div>
      </nav>
      <div className="navigation-footer"><span className="nav-label">Gujarat · Sentinel</span><button className="icon-button collapse-navigation" aria-label={collapsed?'Expand navigation':'Collapse navigation'} onClick={()=>setCollapsed(!collapsed)}>{collapsed?<ChevronRight size={18}/>:<ChevronLeft size={18}/>}</button></div>
    </aside>
  </>;
}
