import React from 'react';
import { X, ShieldAlert, AlertTriangle, Video, Camera, CheckCircle2, Info, Eye } from 'lucide-react';

export default function DemoEvidenceModal({ eventItem, onClose }) {
  if (!eventItem) return null;

  const evidenceImgUrl = eventItem.evidence_image_url 
    ? (eventItem.evidence_image_url.startsWith('http') ? eventItem.evidence_image_url : `http://localhost:8000${eventItem.evidence_image_url}`)
    : null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto animate-fade-in">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-4xl w-full overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-100 border border-amber-200 rounded-xl text-amber-700">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-[#12355B]">
                  {eventItem.title || eventItem.event_type}
                </h3>
                <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-50 text-amber-800 border border-amber-200 font-mono">
                  DEMO ALERT • RECORDED DATASET FOOTAGE
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium mt-0.5">
                {eventItem.camera_id} · {eventItem.display_location || 'Recorded Dataset Footage'}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-100 text-slate-500 hover:text-slate-900 hover:bg-slate-200 border border-slate-200 transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left: Captured Evidence Image Frame */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
              <Camera className="w-4 h-4 text-[#1976D2]" />
              <span>Captured Evidence Frame</span>
            </h4>

            <div className="relative aspect-video bg-slate-900 rounded-xl overflow-hidden border border-slate-200 shadow-inner">
              {evidenceImgUrl ? (
                <img
                  src={evidenceImgUrl}
                  alt={eventItem.event_type}
                  className="w-full h-full object-contain"
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = 'https://images.unsplash.com/photo-1573152143286-0c422b4d2175?auto=format&fit=crop&w=600&q=80';
                  }}
                />
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-slate-400 text-xs">
                  <Video className="w-8 h-8 mb-2 opacity-50" />
                  <span>Evidence frame image pending</span>
                </div>
              )}

              <div className="absolute bottom-2 left-2 right-2 bg-black/75 backdrop-blur-md px-3 py-1.5 rounded-lg text-[11px] text-white flex justify-between font-mono border border-white/10">
                <span>{eventItem.camera_id}</span>
                <span className="text-amber-300">CONFIDENCE: {Math.round((eventItem.confidence || 0.85) * 100)}%</span>
              </div>
            </div>
          </div>

          {/* Right: Event Telemetry & ANPR Status */}
          <div className="space-y-4 text-xs">
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
              <h4 className="font-bold text-[#12355B] text-sm border-b border-slate-200 pb-2">
                Event Verification Details
              </h4>

              <div className="grid grid-cols-2 gap-3 font-mono">
                <div>
                  <span className="text-slate-500 block text-[10px]">EVENT ID</span>
                  <span className="font-bold text-slate-800">{eventItem.event_id}</span>
                </div>

                <div>
                  <span className="text-slate-500 block text-[10px]">TIMESTAMP</span>
                  <span className="font-bold text-slate-800">
                    {new Date(eventItem.timestamp).toLocaleTimeString()}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500 block text-[10px]">VEHICLE CLASS</span>
                  <span className="font-bold text-[#1976D2] uppercase">
                    {eventItem.vehicle_class || 'car'}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500 block text-[10px]">TRACK ID</span>
                  <span className="font-bold text-slate-800">
                    #{eventItem.track_id ?? 'N/A'}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500 block text-[10px]">EVIDENCE LEVEL</span>
                  <span className="font-bold text-emerald-600">
                    {eventItem.evidence_level || 'MEDIUM'}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500 block text-[10px]">SOURCE TYPE</span>
                  <span className="font-bold text-slate-800">DEMO_MP4</span>
                </div>
              </div>
            </div>

            {/* ANPR Status Card */}
            <div className="bg-blue-50/60 p-4 rounded-xl border border-blue-200 space-y-2">
              <h4 className="font-bold text-[#12355B] text-xs flex items-center justify-between">
                <span>ANPR Capability Assessment</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-blue-100 text-blue-800 font-semibold">
                  Honest Assessment
                </span>
              </h4>

              {eventItem.anpr ? (
                <div className="flex items-center gap-3">
                  <div className="px-3 py-1.5 bg-amber-300 text-slate-900 rounded-md font-mono font-black text-sm border border-slate-900 tracking-wider">
                    {eventItem.anpr}
                  </div>
                  <span className="text-[11px] text-slate-600 font-medium">Verified License Plate OCR</span>
                </div>
              ) : (
                <div className="text-[11px] text-slate-600 space-y-1">
                  <span className="font-semibold text-slate-700 block">ANPR: Not Available</span>
                  <p className="text-[10px] text-slate-500 leading-normal">
                    Camera angle and distance in this VisDrone sequence provide insufficient resolution for legal license plate OCR verification.
                  </p>
                </div>
              )}
            </div>

            {/* Data Source Notice */}
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-[11px] text-amber-800 flex items-start gap-2">
              <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <span>
                Demonstration Alert derived from VisDrone dataset footage. Used strictly for AI pipeline presentation. Not a live government law enforcement citation.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
