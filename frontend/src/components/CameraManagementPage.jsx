import React, { useState } from 'react';
import { Sliders, Search, Power, RefreshCw } from 'lucide-react';

export default function CameraManagementPage({ cameras, onToggleConnection, onSelectCamera, onRefresh }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL');

  const filteredCameras = cameras.filter((cam) => {
    const matchesSearch = 
      cam.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (cam.name && cam.name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (cam.location && cam.location.toLowerCase().includes(searchTerm.toLowerCase()));

    const isConnected = cam.connection_status === 'CONNECTED' || cam.connection_status === 'CONNECTING';
    if (filterStatus === 'ONLINE') return matchesSearch && isConnected;
    if (filterStatus === 'OFFLINE') return matchesSearch && !isConnected;
    return matchesSearch;
  });

  const onlineCount = cameras.filter(
    (c) => c.connection_status === 'CONNECTED' || c.connection_status === 'CONNECTING'
  ).length;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Title */}
      <div className="bg-white border border-slate-200 p-5 rounded-2xl card-shadow flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-[#12355B] uppercase tracking-wider flex items-center gap-2">
            <Sliders className="w-5 h-5 text-[#1976D2]" />
            Camera Catalogue & Worker Management ({cameras.length} Total)
          </h2>
          <p className="text-xs text-slate-500 font-medium mt-0.5">
            Control RTSP stream worker processes and manage connected CCTV locations
          </p>
        </div>

        <button
          onClick={onRefresh}
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-[#1976D2] hover:bg-blue-700 text-white text-xs font-semibold shadow-xs transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Sync Catalogue
        </button>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-slate-200 card-shadow">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by ID, Name, Location..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#1976D2]"
          />
        </div>

        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-semibold">
          <button
            onClick={() => setFilterStatus('ALL')}
            className={`px-3 py-1.5 rounded-md transition-all ${filterStatus === 'ALL' ? 'bg-[#1976D2] text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'}`}
          >
            ALL ({cameras.length})
          </button>
          <button
            onClick={() => setFilterStatus('ONLINE')}
            className={`px-3 py-1.5 rounded-md transition-all ${filterStatus === 'ONLINE' ? 'bg-emerald-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'}`}
          >
            ONLINE ({onlineCount})
          </button>
          <button
            onClick={() => setFilterStatus('OFFLINE')}
            className={`px-3 py-1.5 rounded-md transition-all ${filterStatus === 'OFFLINE' ? 'bg-slate-700 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'}`}
          >
            OFFLINE ({cameras.length - onlineCount})
          </button>
        </div>
      </div>

      {/* Catalogue Table */}
      <div className="bg-white border border-slate-200 rounded-2xl card-shadow overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-50 text-slate-600 border-b border-slate-200 font-semibold">
              <th className="p-4">Camera ID</th>
              <th className="p-4">Name / Location</th>
              <th className="p-4">Stream URL</th>
              <th className="p-4">Connection Status</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-medium">
            {filteredCameras.map((cam) => {
              const isConnected = cam.connection_status === 'CONNECTED' || cam.connection_status === 'CONNECTING';

              return (
                <tr key={cam.id} className="hover:bg-slate-50 transition-colors">
                  <td className="p-4 font-bold text-[#1976D2] font-mono">{cam.id.toUpperCase()}</td>
                  <td className="p-4">
                    <div className="font-bold text-slate-900">{cam.name || cam.id}</div>
                    <div className="text-[11px] text-slate-500">{cam.location || 'Junagadh Surveillance Network'}</div>
                  </td>
                  <td className="p-4 font-mono text-slate-500 text-[11px] max-w-xs truncate">
                    {cam.rtsp_url || `rtsp://103.250.160.189:8554/stream/${cam.id}`}
                  </td>
                  <td className="p-4">
                    <span className={`px-2.5 py-1 text-[11px] font-semibold rounded-lg border inline-flex items-center gap-1.5 ${
                      isConnected
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-slate-100 text-slate-600 border-slate-200'
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-live-pulse' : 'bg-slate-400'}`} />
                      {isConnected ? 'ONLINE' : 'DISCONNECTED'}
                    </span>
                  </td>
                  <td className="p-4 text-right space-x-2">
                    <button
                      onClick={() => onToggleConnection(cam.id, !isConnected)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                        isConnected
                          ? 'bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200'
                          : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200'
                      }`}
                    >
                      {isConnected ? 'Disconnect' : 'Connect Worker'}
                    </button>
                    <button
                      onClick={() => onSelectCamera(cam)}
                      className="px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-[#1976D2] border border-blue-200 text-xs font-semibold transition-all"
                    >
                      Focus View
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
