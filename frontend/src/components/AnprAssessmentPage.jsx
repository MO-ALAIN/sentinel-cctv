import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { SearchCode, CheckCircle2, AlertTriangle, ShieldCheck, FileCheck, Check, RefreshCw, Video } from 'lucide-react';

export default function AnprAssessmentPage() {
  const [anprData, setAnprData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const [error, setError] = useState('');
  const fetchAnprStatus = async () => {
    setIsLoading(true); setError('');
    try {
      const data = await api('/api/cameras/anpr-status');
      if (!Array.isArray(data.cameras)) throw new Error('Assessment response is incomplete.');
      setAnprData(data);
    } catch (e) {
      setAnprData(null); setError(e.message || 'Assessment unavailable.');
    } finally { setIsLoading(false); }
  };
  useEffect(() => { fetchAnprStatus(); }, []);
  const cameras = anprData?.cameras || [];

  const getStatusBadge = (status) => {
    switch (status) {
      case 'ANPR_READY':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200">🟢 ANPR READY</span>;
      case 'ANPR_POTENTIAL':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-lg bg-amber-50 text-amber-800 border border-amber-200">🟡 ANPR POTENTIAL</span>;
      case 'ANPR_LIMITED':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-lg bg-orange-50 text-orange-800 border border-orange-200">🟠 ANPR LIMITED</span>;
      default:
        return <span className="px-2.5 py-1 text-xs font-bold rounded-lg bg-rose-50 text-rose-800 border border-rose-200">🔴 ANPR UNSUITABLE</span>;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Title Header */}
      <div className="bg-white border border-slate-200 p-5 rounded-2xl card-shadow flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-[#12355B] uppercase tracking-wider flex items-center gap-2">
            <SearchCode className="w-5 h-5 text-[#1976D2]" />
            License Plate Recognition & Camera Quality Assessment
          </h2>
          <p className="text-xs text-slate-500 font-medium mt-0.5">
            Latest saved camera assessment. These diagnostics are separate from independently labelled recognition accuracy.
          </p>
        </div>
        <button
          onClick={fetchAnprStatus}
          disabled={isLoading}
          className="px-3.5 py-1.5 text-xs font-semibold bg-[#1976D2] hover:bg-blue-700 text-white rounded-lg shadow-xs transition-all flex items-center gap-2"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh results</span>
        </button>
      </div>

      {error && <p className="police-message error" role="alert">Could not load assessment: {error}</p>}
      {!isLoading && !error && !cameras.length && <div className="police-empty">No camera assessment has been run in this process. Refresh results after running a camera assessment.</div>}
      <p className="police-muted">Plate resolution and quality scores help diagnose a camera. Matching reads can still be wrong; review evidence and measure misses and incorrect readings on labelled footage.</p>

      {/* Per-Camera Intelligent ANPR Status Table */}
      <div className="bg-white border border-slate-200 rounded-2xl card-shadow overflow-hidden">
        <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-xs font-bold text-[#12355B] uppercase tracking-wider flex items-center gap-2">
            <Video className="w-4 h-4 text-[#1976D2]" />
            Camera-Wise ANPR Capability Report
          </h3>
          <span className="text-xs font-mono text-slate-500 font-semibold">{cameras.length} Cameras Evaluated</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100/80 border-b border-slate-200 text-[#12355B] font-bold uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Camera Feed</th>
                <th className="py-3 px-4">ANPR Status</th>
                <th className="py-3 px-4">Plate Candidates</th>
                <th className="py-3 px-4">Max Resolution</th>
                <th className="py-3 px-4">Quality Score</th>
                <th className="py-3 px-4">OCR Attempts</th>
                <th className="py-3 px-4">Confirmed Plates</th>
                <th className="py-3 px-4">Status Rationale</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {cameras.map((cam, idx) => (
                <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3.5 px-4 font-bold text-[#12355B]">
                    {cam.camera_name || cam.camera_id}
                    <span className="block text-[10px] text-slate-400 font-mono">{cam.camera_id}</span>
                  </td>
                  <td className="py-3.5 px-4">{getStatusBadge(cam.anpr_status)}</td>
                  <td className="py-3.5 px-4 font-mono font-semibold text-slate-700">{cam.plate_candidates || 0}</td>
                  <td className="py-3.5 px-4 font-mono text-slate-600">{cam.best_resolution_px || 0} px</td>
                  <td className="py-3.5 px-4">
                    <div className="w-24 bg-slate-200 rounded-full h-2 overflow-hidden mb-1">
                      <div
                        className="bg-[#1976D2] h-full rounded-full"
                        style={{ width: `${Math.min(100, cam.best_quality_score || cam.anpr_score || 0)}%` }}
                      />
                    </div>
                    <span className="font-mono font-bold text-slate-700 text-[10px]">
                      {cam.best_quality_score || cam.anpr_score || 0}/100
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-600">{cam.ocr_attempts || 0}</td>
                  <td className="py-3.5 px-4 font-mono font-bold text-emerald-700">{cam.confirmed_plates || 0}</td>
                  <td className="py-3.5 px-4 text-[11px] text-slate-600 font-medium max-w-xs">{cam.rationale}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
