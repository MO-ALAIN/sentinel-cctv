import React, { useState, useEffect } from 'react';
import { X, Video, Car, Bike, Bus, Truck, ShieldCheck, AlertCircle, Radio, RefreshCw } from 'lucide-react';

export default function CameraFocusModal({ camera, analytics, onClose, onToggleConnection, streamMode = 'LIVE' }) {
  if (!camera) return null;

  const [telemetry, setTelemetry] = useState(analytics || null);
  const [isSyncing, setIsSyncing] = useState(false);

  const isConnected = camera.connection_status === 'CONNECTED' || camera.connection_status === 'CONNECTING' || camera.mode === 'VISDRONE_DEMO';
  const streamUrl = camera.id?.startsWith('CAM-DEMO-') || streamMode === 'DEMO'
    ? `/api/demo/cameras/${camera.id}/annotated` 
    : `/api/cameras/${camera.id}/annotated`;

  // STEP 8: Active 1000ms polling for /api/analytics/{camera_id} while modal is open
  useEffect(() => {
    let isMounted = true;

    const fetchLiveTelemetry = async () => {
      setIsSyncing(true);
      try {
        const res = await fetch(`/api/analytics/${camera.id}`);
        if (res.ok) {
          const data = await res.json();
          if (isMounted && data) {
            setTelemetry(data);
          }
        }
      } catch (err) {
        // Fallback to direct http://localhost:8000
        try {
          const directRes = await fetch(`http://localhost:8000/api/analytics/${camera.id}`);
          if (directRes.ok) {
            const data = await directRes.json();
            if (isMounted && data) {
              setTelemetry(data);
            }
          }
        } catch (e) {
          console.warn(`Telemetry polling error for ${camera.id}:`, e);
        }
      } finally {
        if (isMounted) setIsSyncing(false);
      }
    };

    fetchLiveTelemetry();
    const interval = setInterval(fetchLiveTelemetry, 1000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [camera.id]);

  const currentAnalytics = telemetry || analytics;

  const classCounts = currentAnalytics?.unique_vehicle_breakdown || { cars: 0, motorcycles: 0, buses: 0, trucks: 0 };
  const density = currentAnalytics?.traffic_density || 'LOW';
  const activeVehicles = currentAnalytics?.active_vehicles || 0;
  const totalUnique = currentAnalytics?.total_unique_vehicles || 0;
  const flowRate = currentAnalytics?.flow_metrics?.vehicles_per_minute || 0.0;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto animate-fade-in">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-5xl w-full overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100/80 border border-blue-200 rounded-xl text-[#1976D2]">
              <Video className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-[#12355B]">{camera.name || camera.id}</h3>
                <span className="text-xs font-mono font-bold text-[#1976D2]">({camera.id})</span>
                <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-blue-50 text-blue-800 border border-blue-200 font-mono">
                  {camera.source_type || "RECORDED DEMO"}
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">{camera.location || 'Location unavailable'}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className={`px-3 py-1 text-xs font-semibold rounded-lg border ${
              isConnected ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-100 text-slate-600 border-slate-300'
            }`}>
              ● {isConnected ? 'CONNECTED' : 'OFFLINE'}
            </span>
            <button
              onClick={onClose}
              aria-label="Close camera view"
              className="p-1.5 rounded-lg bg-slate-100 text-slate-500 hover:text-slate-900 hover:bg-slate-200 border border-slate-200 transition-all"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Annotated Stream Area */}
          <div className="lg:col-span-2 flex flex-col gap-4">
            <div className="relative aspect-video bg-slate-900 rounded-2xl overflow-hidden border border-slate-200 shadow-inner flex items-center justify-center">
              {isConnected ? (
                <img
                  src={streamUrl}
                  alt={`Annotated stream for ${camera.id}`}
                  className="w-full h-full object-contain"
                  onError={(e) => {
                    e.target.style.display = "none";
                    const errDiv = e.target.nextSibling;
                    if (errDiv) errDiv.style.display = "flex";
                  }}
                  onLoad={(e) => {
                    e.target.style.display = "block";
                    const errDiv = e.target.nextSibling;
                    if (errDiv) errDiv.style.display = "none";
                  }}
                />
              ) : null}

              {/* Light Gray Loading Placeholder */}
              <div className={`${isConnected ? 'hidden' : 'flex'} absolute inset-0 bg-slate-100 flex flex-col items-center justify-center p-6 text-center text-slate-500`}>
                <div className="p-4 bg-blue-50 rounded-full text-[#1976D2] mb-2">
                  <Video className="w-8 h-8" />
                </div>
                <span className="text-sm font-bold text-[#12355B]">Connecting to CCTV Stream...</span>
                <span className="text-xs text-slate-500 mt-1 font-medium">Establishing secure video connection</span>
                <button
                  onClick={() => onToggleConnection(camera.id, true)}
                  className="mt-3 px-4 py-2 bg-[#1976D2] hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-all"
                >
                  Connect Stream Now
                </button>
              </div>
            </div>

            {/* RTSP Stream Control */}
            <div className="flex items-center justify-between bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs">
              <span className="text-slate-600 text-[11px]">Source: {camera.source_type || 'UNKNOWN'} · Camera {camera.id}</span>
              <button
                onClick={() => onToggleConnection(camera.id, !isConnected)}
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                  isConnected
                    ? 'bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200'
                    : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200'
                }`}
              >
                {isConnected ? 'Disconnect Stream' : 'Connect Stream'}
              </button>
            </div>
          </div>

          {/* Right Sidebar Telemetry */}
          <div className="flex flex-col gap-4">
            {/* Status & Density Card */}
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-[#12355B] uppercase tracking-wider">Live Telemetry</h4>
                <span className="text-[10px] text-slate-400 flex items-center gap-1 font-mono">
                  <RefreshCw className={`w-3 h-3 ${isSyncing ? 'animate-spin text-[#1976D2]' : ''}`} />
                  1s Sync
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-medium block mb-0.5">Active Vehicles</span>
                  <span className="text-2xl font-extrabold text-[#1976D2] font-mono">{activeVehicles}</span>
                </div>
                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-medium block mb-0.5">Traffic Status</span>
                  <span className="text-xs font-bold font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 inline-block">
                    {density}
                  </span>
                </div>
              </div>

              <div className="bg-white p-3 rounded-lg border border-slate-200 flex items-center justify-between">
                <span className="text-xs text-slate-600 font-medium">Total Unique Tracked</span>
                <span className="text-base font-bold text-slate-900 font-mono">{totalUnique}</span>
              </div>

              <div className="bg-white p-3 rounded-lg border border-slate-200 flex items-center justify-between">
                <span className="text-xs text-slate-600 font-medium">Traffic Flow Rate</span>
                <span className="text-base font-bold text-emerald-700 font-mono">{flowRate} VPM</span>
              </div>
            </div>

            {/* Vehicle Class Breakdown */}
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
              <h4 className="text-xs font-bold text-[#12355B] uppercase tracking-wider">Vehicle Distribution</h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex items-center gap-2 p-2.5 bg-white rounded-lg border border-slate-200">
                  <Car className="w-4 h-4 text-[#1976D2]" />
                  <div>
                    <span className="text-[10px] text-slate-500 block">Cars</span>
                    <span className="font-bold text-slate-800 font-mono">{classCounts.cars || classCounts.car || 0}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 p-2.5 bg-white rounded-lg border border-slate-200">
                  <Bike className="w-4 h-4 text-emerald-600" />
                  <div>
                    <span className="text-[10px] text-slate-500 block">Motorcycles</span>
                    <span className="font-bold text-slate-800 font-mono">{classCounts.motorcycles || classCounts.motorcycle || 0}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 p-2.5 bg-white rounded-lg border border-slate-200">
                  <Bus className="w-4 h-4 text-amber-600" />
                  <div>
                    <span className="text-[10px] text-slate-500 block">Buses</span>
                    <span className="font-bold text-slate-800 font-mono">{classCounts.buses || classCounts.bus || 0}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 p-2.5 bg-white rounded-lg border border-slate-200">
                  <Truck className="w-4 h-4 text-indigo-600" />
                  <div>
                    <span className="text-[10px] text-slate-500 block">Trucks</span>
                    <span className="font-bold text-slate-800 font-mono">{classCounts.trucks || classCounts.truck || 0}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 p-2.5 bg-white rounded-lg border border-slate-200 col-span-2">
                  <span className="text-sm">🛺</span>
                  <div>
                    <span className="text-[10px] text-slate-500 block">Auto Rickshaws</span>
                    <span className="font-bold text-amber-600 font-mono">{classCounts.auto_rickshaws || classCounts.auto_rickshaw || 0}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
