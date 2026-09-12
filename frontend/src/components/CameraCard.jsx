import React, { useState, useEffect } from 'react';
import { Play, Square, Activity, MapPin, Eye, AlertTriangle } from 'lucide-react';

export default function CameraCard({ camera, onToggleConnection }) {
  const [telemetry, setTelemetry] = useState(camera.stream_telemetry || null);
  const [isConnected, setIsConnected] = useState(
    camera.connection_status === 'CONNECTED' || camera.connection_status === 'CONNECTING'
  );
  const [isProcessing, setIsProcessing] = useState(false);

  // Poll status when connected
  useEffect(() => {
    let interval;
    if (isConnected) {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`/api/cameras/${camera.id}/status`);
          if (res.ok) {
            const data = await res.json();
            setTelemetry(data);
            if (data.status === 'DISCONNECTED') {
              setIsConnected(false);
            }
          }
        } catch (e) {
          console.error(`Failed to poll status for ${camera.id}`, e);
        }
      }, 1000);
    } else {
      setTelemetry(null);
    }
    return () => clearInterval(interval);
  }, [isConnected, camera.id]);

  const handleToggle = async () => {
    setIsProcessing(true);
    try {
      await onToggleConnection(camera.id, !isConnected);
      setIsConnected(!isConnected);
    } catch (e) {
      console.error('Connection toggle error:', e);
    } finally {
      setIsProcessing(false);
    }
  };

  const status = telemetry?.status || camera.connection_status || 'DISCONNECTED';
  const fps = telemetry?.fps || 0;
  const framesReceived = telemetry?.frames_received || 0;
  const resolution = telemetry?.resolution || 'N/A';

  return (
    <div className="bg-[#111823] border border-[#1e2a3a] rounded-xl overflow-hidden shadow-lg flex flex-col hover:border-blue-900/60 transition">
      {/* Header bar */}
      <div className="p-3 bg-[#0d131d] border-b border-[#1e2a3a] flex items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800/50">
              {camera.id}
            </span>
            <h3 className="text-sm font-semibold text-white truncate max-w-[180px]">{camera.name}</h3>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-[#7d8da3] mt-0.5">
            <MapPin className="w-3 h-3 text-blue-400" />
            <span className="truncate max-w-[200px]">{camera.location}</span>
          </div>
        </div>

        {/* Status Indicator */}
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${
            status === 'CONNECTED' ? 'bg-emerald-500 animate-pulse' :
            status === 'CONNECTING' || status === 'RECONNECTING' ? 'bg-amber-400 animate-ping' :
            'bg-slate-600'
          }`} />
          <span className="text-[11px] font-mono font-semibold uppercase text-slate-300">
            {status}
          </span>
        </div>
      </div>

      {/* Video Stream Area */}
      <div className="relative aspect-video bg-black/80 flex items-center justify-center overflow-hidden">
        {isConnected ? (
          <img
            src={`/api/cameras/${camera.id}/mjpeg?t=${Date.now()}`}
            alt={`Live RTSP stream ${camera.id}`}
            className="w-full h-full object-cover"
            onError={(e) => {
              // Retry on image error
              console.warn(`MJPEG stream retry for ${camera.id}`);
            }}
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-[#5c6b86] p-4 text-center">
            <Eye className="w-8 h-8 opacity-40" />
            <p className="text-xs">RTSP Stream Idle</p>
            <p className="text-[10px] font-mono text-slate-500">{camera.rtsp_url}</p>
          </div>
        )}

        {/* Live Overlay Telemetry */}
        {isConnected && (
          <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between px-2.5 py-1 bg-black/70 backdrop-blur-md rounded border border-white/10 text-[10px] font-mono text-white">
            <div className="flex items-center gap-2">
              <span className="text-emerald-400 font-bold">● LIVE RTSP</span>
              <span className="text-slate-400">|</span>
              <span className="text-sky-300">{resolution}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-amber-300">{fps} FPS</span>
              <span className="text-slate-400">|</span>
              <span className="text-slate-300">{framesReceived} FRS</span>
            </div>
          </div>
        )}
      </div>

      {/* Footer controls & stream specs */}
      <div className="p-3 bg-[#0f1622] border-t border-[#1e2a3a] flex items-center justify-between gap-2 text-xs">
        <div className="text-[11px] text-[#7d8da3] font-mono truncate">
          RTSP: <span className="text-slate-400">rtsp://.../{camera.id}</span>
        </div>

        <button
          onClick={handleToggle}
          disabled={isProcessing}
          className={`px-3 py-1 rounded-lg font-semibold flex items-center gap-1.5 transition text-xs ${
            isConnected
              ? 'bg-rose-950/80 hover:bg-rose-900 border border-rose-800 text-rose-300'
              : 'bg-emerald-600 hover:bg-emerald-500 text-white'
          }`}
        >
          {isConnected ? (
            <>
              <Square className="w-3 h-3 fill-current" />
              Disconnect
            </>
          ) : (
            <>
              <Play className="w-3 h-3 fill-current" />
              Connect RTSP
            </>
          )}
        </button>
      </div>
    </div>
  );
}
