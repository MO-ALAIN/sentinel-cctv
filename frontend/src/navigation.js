import { House, Video, Search, Bell, ShieldCheck, MapPin, LayoutDashboard, BarChart3, AlertTriangle, Sliders, ScanLine, Activity, Film } from 'lucide-react';
export const navigation = [
  {id:'home',label:'Overview',icon:House,group:'Workspace'},
  {id:'cameras',label:'Live Cameras',icon:Video,group:'Workspace'},
  {id:'vehicle-trace',label:'Find vehicle',icon:Search,group:'Workspace'},
  {id:'live-alerts',label:'Alerts',icon:Bell,group:'Workspace'},
  {id:'watchlist',label:'Watchlist',icon:ShieldCheck,group:'Workspace'},
  {id:'gis',label:'Camera registry',icon:MapPin,group:'Workspace'},
  {id:'dashboard',label:'Monitoring dashboard',icon:LayoutDashboard,group:'More tools'},
  {id:'analytics',label:'Traffic analytics',icon:BarChart3,group:'More tools'},
  {id:'incidents',label:'Incident review',icon:AlertTriangle,group:'More tools'},
  {id:'camera-management',label:'Connection management',icon:Sliders,group:'More tools'},
  {id:'anpr-assessment',label:'Plate-reading assessment',icon:ScanLine,group:'More tools'},
  {id:'demo',label:'Recorded demos',icon:Film,group:'More tools'},
  {id:'system-status',label:'System status',icon:Activity,group:'More tools'},
];
export const pageFromHash = () => {
  const id=window.location.hash.slice(1);
  return navigation.some(p=>p.id===id)?id:'home';
};
