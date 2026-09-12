import React, { useState, useEffect } from 'react';
import { Video, Activity, Cpu, RefreshCw, Maximize2, Minimize2, CheckCircle2, ShieldAlert, Layers, Play, AlertCircle } from 'lucide-react';

export default function DemoScenarioViewer({ scenario, onSelectScenario, isPresentationMode, setIsPresentationMode }) {
  if (!scenario) return null;

  const [telemetry, setTelemetry] = useState(null);
  const [streamType, setStreamType] = useState('ANNOTATED'); // 'ANNOTATED' or 'RAW_MP4'
  const [isStreamLoaded, setIsStreamLoaded] = useState(false);
  const [streamError, setStreamError] = useState(null);
  const [keyTimestamp, setKeyTimestamp] = useState(Date.now());

  const camera_id = scenario.id || scenario.camera_id || "CAM-DEMO-01";
  
  // Relative paths leverage Vite dev server proxy to http://127.0.0.1:8000 cleanly without CORS issues
  const annotatedStreamUrl = `/api/demo/cameras/${camera_id}/annotated?t=${keyTimestamp}`;
  const rawVideoUrl = `/api/demo/cameras/${camera_id}/video`;

  useEffect(() => {
    let isMounted = true;
    setIsStreamLoaded(false);
    setStreamError(null);
    setKeyTimestamp(Date.now());

    // 1. Activate active scenario focus on backend for full 25 FPS GPU inference
    fetch(`/api/demo/cameras/${camera_id}/activate`, { method: 'POST' })
      .catch(err => console.warn(`Activation fetch warning for ${camera_id}:`, err));

    // 2. Poll telemetry every 1500ms
    const fetchScenarioAnalytics = async () => {
      try {
        const res = await fetch(`/api/demo/cameras/${camera_id}/analytics`);
        if (res.ok) {
          const data = await res.json();
          if (isMounted && data) {
            setTelemetry(data);
          }
        }
      } catch (err) {
        console.warn(`Analytics fetch warning for ${camera_id}:`, err);
      }
    };

    fetchScenarioAnalytics();
    const interval = setInterval(fetchScenarioAnalytics, 1500);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [camera_id]);

  const activeVehicles = telemetry?.active_vehicles ?? scenario.active_vehicles ?? 0;
  const uniqueVehicles = telemetry?.total_unique_vehicles ?? scenario.total_unique_vehicles ?? 0;
  const density = telemetry?.traffic_density ?? scenario.traffic_density ?? 'LOW';
  const vpm = telemetry?.flow_metrics?.vehicles_per_minute ?? 0.0;
  const breakdown = telemetry?.unique_vehicle_breakdown || { cars: 0, motorcycles: 0, buses: 0, trucks: 0, auto_rickshaws: 0 };

  return (
    <div className={`bg-white rounded-2xl border border-slate-200 card-shadow overflow-hidden transition-all duration-300 ${
      isPresentationMode ? 'fixed inset-4 z-50 shadow-2xl flex flex-col' : 'space-y-4 p-5'
    }`}>
      {/* Viewer Header */}
      <div className={`flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100 ${isPresentationMode ? 'p-4 bg-slate-50' : ''}`}>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-[#1976D2] text-white rounded-xl shadow-xs">
            <Video className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-[#12355B]">
                {scenario.name || `Traffic Scenario ${camera_id.slice(-2)}`}
              </h3>
              <span className="text-xs font-mono font-bold text-[#1976D2]">({camera_id})</span>
              <span className="px-2.5 py-0.5 text-[10px] font-bold rounded-full bg-amber-50 text-amber-800 border border-amber-200">
                DEMO MODE • RECORDED DATASET FOOTAGE
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium mt-0.5">
              Source: <span className="font-bold text-slate-700">VisDrone Dataset</span> ({scenario.video_file || `${camera_id.toLowerCase()}.mp4`})
            </p>
          </div>
        </div>

        {/* Controls Bar */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
          {/* Stream Type Selector */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200">
            <button
              onClick={() => setStreamType('ANNOTATED')}
              className={`px-3 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                streamType === 'ANNOTATED' ? 'bg-[#1976D2] text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>AI ANNOTATED STREAM</span>
            </button>
            <button
              onClick={() => setStreamType('RAW_MP4')}
              className={`px-3 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                streamType === 'RAW_MP4' ? 'bg-indigo-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Play className="w-3.5 h-3.5" />
              <span>ORIGINAL MP4 RECORDING</span>
            </button>
          </div>

          <button
            onClick={() => setIsPresentationMode(!isPresentationMode)}
            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg border border-slate-200 transition-all flex items-center gap-1.5"
            title="Toggle Large Presentation Mode"
          >
            {isPresentationMode ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            <span>{isPresentationMode ? 'Exit Presentation' : 'Presentation Mode'}</span>
          </button>
        </div>
      </div>

      {/* Main Body: Video Player + Analytics Sidebar */}
      <div className={`grid grid-cols-1 lg:grid-cols-3 gap-6 ${isPresentationMode ? 'p-6 flex-1 overflow-y-auto' : ''}`}>
        {/* Large Video Player */}
        <div className="lg:col-span-2 space-y-3 flex flex-col">
          <div className="relative aspect-video bg-slate-950 rounded-2xl overflow-hidden border border-slate-200 shadow-md group flex-1 flex items-center justify-center">
            {streamType === 'ANNOTATED' ? (
              <img
                key={camera_id}
                src={annotatedStreamUrl}
                alt={scenario.name}
                className="w-full h-full object-contain bg-slate-950"
                onLoad={() => {
                  setIsStreamLoaded(true);
                  setStreamError(null);
                }}
                onError={(e) => {
                  console.warn("Annotated stream connection retry for:", camera_id);
                  // Softly refresh src parameter without re-creating DOM node if error occurs
                  setStreamError("Reconnecting stream...");
                }}
              />
            ) : (
              <video
                key={`video-${camera_id}`}
                src={rawVideoUrl}
                controls
                autoPlay
                loop
                className="w-full h-full object-contain bg-slate-950"
                onCanPlay={() => setIsStreamLoaded(true)}
              />
            )}

            {/* Top Video Overlay Badge */}
            <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none">
              <span className="px-3 py-1 bg-amber-500/90 text-white font-bold text-xs rounded-lg shadow-sm backdrop-blur-md flex items-center gap-1.5">
                <Video className="w-3.5 h-3.5" />
                {streamType === 'ANNOTATED' ? 'DEMO MODE — AI ANNOTATED STREAM' : 'ORIGINAL VISDRONE MP4 RECORDING'}
              </span>
              <span className="px-2.5 py-1 bg-black/70 text-white font-mono text-xs rounded-lg backdrop-blur-md border border-white/10">
                {streamType === 'ANNOTATED' ? 'YOLOv8 CUDA + ByteTrack' : 'H.264 Video Source'}
              </span>
            </div>

            {/* Bottom Overlay Telemetry Bar */}
            <div className="absolute bottom-3 left-3 right-3 bg-black/80 backdrop-blur-md px-4 py-2 rounded-xl text-white text-xs border border-white/10 flex items-center justify-between font-mono">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="font-bold text-sky-200 uppercase">{density} DENSITY</span>
              </div>
              <div className="flex items-center gap-4 text-xs">
                <span>ACTIVE: <strong className="text-amber-300">{activeVehicles}</strong></span>
                <span>UNIQUE: <strong className="text-emerald-300">{uniqueVehicles}</strong></span>
                <span>VPM: <strong className="text-sky-300">{vpm}</strong></span>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-500 px-1 font-medium">
            <span>Scenario: {scenario.scenario || 'VisDrone Demonstration'}</span>
            <span>Mode: {streamType === 'ANNOTATED' ? 'YOLO CUDA Inference' : 'HTML5 Native MP4'}</span>
          </div>
        </div>

        {/* Real-Time Telemetry & Vehicle Breakdown Sidebar */}
        <div className="space-y-4">
          {/* Key Metrics Grid */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
            <h4 className="font-bold text-[#12355B] text-xs uppercase tracking-wider flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-[#1976D2]" />
              <span>Real-Time Traffic Telemetry</span>
            </h4>

            <div className="grid grid-cols-2 gap-3 font-mono text-xs">
              <div className="bg-white p-3 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[10px]">ACTIVE VEHICLES</span>
                <span className="text-xl font-bold text-[#12355B]">{activeVehicles}</span>
              </div>

              <div className="bg-white p-3 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[10px]">TOTAL TRACKED</span>
                <span className="text-xl font-bold text-[#1976D2]">{uniqueVehicles}</span>
              </div>

              <div className="bg-white p-3 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[10px]">TRAFFIC DENSITY</span>
                <span className={`text-sm font-bold uppercase ${
                  density === 'HIGH' || density === 'VERY_HIGH' ? 'text-amber-600' : 'text-emerald-600'
                }`}>
                  {density}
                </span>
              </div>

              <div className="bg-white p-3 rounded-lg border border-slate-200">
                <span className="text-slate-500 block text-[10px]">VEHICLES / MIN</span>
                <span className="text-sm font-bold text-slate-800">{vpm}</span>
              </div>
            </div>
          </div>

          {/* Vehicle Class Breakdown */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2.5">
            <h4 className="font-bold text-[#12355B] text-xs uppercase tracking-wider flex items-center justify-between">
              <span>Vehicle Classification</span>
              <span className="text-[10px] font-mono text-slate-500">ByteTrack IDs</span>
            </h4>

            <div className="space-y-1.5 text-xs font-mono">
              <div className="flex items-center justify-between bg-white p-2 rounded-lg border border-slate-200">
                <span className="text-slate-600">🚗 Cars</span>
                <span className="font-bold text-[#12355B]">{breakdown.cars || 0}</span>
              </div>
              <div className="flex items-center justify-between bg-white p-2 rounded-lg border border-slate-200">
                <span className="text-slate-600">🏍️ Motorcycles</span>
                <span className="font-bold text-[#12355B]">{breakdown.motorcycles || 0}</span>
              </div>
              <div className="flex items-center justify-between bg-white p-2 rounded-lg border border-slate-200">
                <span className="text-slate-600">🚌 Buses</span>
                <span className="font-bold text-[#12355B]">{breakdown.buses || 0}</span>
              </div>
              <div className="flex items-center justify-between bg-white p-2 rounded-lg border border-slate-200">
                <span className="text-slate-600">🚚 Trucks</span>
                <span className="font-bold text-[#12355B]">{breakdown.trucks || 0}</span>
              </div>
              <div className="flex items-center justify-between bg-white p-2 rounded-lg border border-slate-200">
                <span className="text-slate-600">🛺 Auto Rickshaws</span>
                <span className="font-bold text-[#12355B]">{breakdown.auto_rickshaws || 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
