import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, Clock, Camera, ShieldAlert } from 'lucide-react';

export default function IncidentCenterPage({ eventsList, eventsSummary }) {
  const [selectedFilter, setSelectedFilter] = useState('ALL');

  const activeIncidentsCount = eventsSummary?.active_events || 0;
  const sessionEventsCount = eventsSummary?.session_events || 0;
  const byType = eventsSummary?.by_type || {};

  const filteredEvents = (eventsList || []).filter((e) => {
    if (selectedFilter === 'ALL') return true;
    if (selectedFilter === 'ACTIVE') return e.status === 'ACTIVE';
    return e.event_type === selectedFilter;
  });

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Title */}
      <div className="bg-white border border-slate-200 p-5 rounded-2xl card-shadow flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-[#12355B] uppercase tracking-wider flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            Intelligent Incident & Event Center
          </h2>
          <p className="text-xs text-slate-500 font-medium mt-0.5">
            Automated traffic anomaly detection, wrong-way movement alerts, and congestion indicators
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-semibold">
          <span className="px-3 py-1 bg-slate-100 border border-slate-200 rounded-lg text-slate-700">
            Session Events: <strong className="text-[#1976D2] font-mono">{sessionEventsCount}</strong>
          </span>
          <span className="px-3 py-1 bg-slate-100 border border-slate-200 rounded-lg text-slate-700">
            Active Alerts: <strong className={`font-mono ${activeIncidentsCount > 0 ? 'text-rose-600' : 'text-emerald-700'}`}>{activeIncidentsCount}</strong>
          </span>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2 bg-white p-2.5 rounded-2xl border border-slate-200 text-xs font-semibold card-shadow">
        <button
          onClick={() => setSelectedFilter('ALL')}
          className={`px-3.5 py-1.5 rounded-xl transition-all ${selectedFilter === 'ALL' ? 'bg-[#1976D2] text-white shadow-xs' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'}`}
        >
          ALL EVENTS ({eventsList?.length || 0})
        </button>

        <button
          onClick={() => setSelectedFilter('ACTIVE')}
          className={`px-3.5 py-1.5 rounded-xl transition-all ${selectedFilter === 'ACTIVE' ? 'bg-rose-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'}`}
        >
          ACTIVE ({activeIncidentsCount})
        </button>

        <button
          onClick={() => setSelectedFilter('STATIONARY_VEHICLE')}
          className={`px-3.5 py-1.5 rounded-xl transition-all ${selectedFilter === 'STATIONARY_VEHICLE' ? 'bg-amber-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'}`}
        >
          STATIONARY ({byType['STATIONARY_VEHICLE'] || 0})
        </button>

        <button
          onClick={() => setSelectedFilter('WRONG_DIRECTION')}
          className={`px-3.5 py-1.5 rounded-xl transition-all ${selectedFilter === 'WRONG_DIRECTION' ? 'bg-indigo-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'}`}
        >
          WRONG DIRECTION ({byType['WRONG_DIRECTION'] || 0})
        </button>

        <button
          onClick={() => setSelectedFilter('POSSIBLE_CONGESTION')}
          className={`px-3.5 py-1.5 rounded-xl transition-all ${selectedFilter === 'POSSIBLE_CONGESTION' ? 'bg-yellow-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'}`}
        >
          POSSIBLE CONGESTION ({byType['POSSIBLE_CONGESTION'] || 0})
        </button>

        <button
          onClick={() => setSelectedFilter('POSSIBLE_INCIDENT')}
          className={`px-3.5 py-1.5 rounded-xl transition-all ${selectedFilter === 'POSSIBLE_INCIDENT' ? 'bg-rose-700 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'}`}
        >
          POSSIBLE INCIDENT ({byType['POSSIBLE_INCIDENT'] || 0})
        </button>
      </div>

      {/* Main Incident Display */}
      {filteredEvents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredEvents.map((evt) => (
            <div
              key={evt.event_id}
              className="bg-white border border-slate-200 rounded-2xl p-4 card-shadow space-y-3 flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="px-2.5 py-0.5 text-[10px] font-bold font-mono rounded bg-rose-50 text-rose-700 border border-rose-200">
                    {evt.event_type}
                  </span>
                  <span className="text-[11px] font-mono text-slate-500 flex items-center gap-1">
                    <Clock className="w-3 h-3 text-slate-400" />
                    {new Date(evt.timestamp).toLocaleTimeString()}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <Camera className="w-4 h-4 text-[#1976D2]" />
                  <span className="text-sm font-bold text-slate-900 font-mono">{evt.camera_id}</span>
                  {evt.vehicle_type && (
                    <span className="text-xs text-slate-500">({evt.vehicle_type.toUpperCase()} #{evt.track_id})</span>
                  )}
                </div>

                <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-xl border border-slate-200 leading-relaxed font-medium">
                  {evt.metadata?.reason || `Event logged for camera ${evt.camera_id} under strict rule parameters.`}
                </p>
              </div>

              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono text-slate-500">
                <span>Confidence: {(evt.confidence * 100).toFixed(0)}%</span>
                <span className={`px-2 py-0.5 rounded font-bold ${evt.status === 'ACTIVE' ? 'bg-rose-100 text-rose-800' : 'bg-slate-100 text-slate-600'}`}>
                  {evt.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Zero Incidents Clean Professional State */
        <div className="bg-white border border-emerald-200 rounded-2xl p-12 text-center flex flex-col items-center justify-center space-y-4 card-shadow">
          <div className="p-4 bg-emerald-50 rounded-full text-emerald-600 border border-emerald-200">
            <CheckCircle2 className="w-12 h-12" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-emerald-800">🟢 All Systems Operating Normally</h3>
            <p className="text-xs font-semibold text-emerald-700">No active traffic incidents detected</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed pt-1">
              CCTV feeds are being continuously monitored for unusual traffic patterns and events.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
