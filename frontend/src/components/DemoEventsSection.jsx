import React, { useState, useEffect } from 'react';
import { ShieldAlert, AlertTriangle, Eye, RefreshCw, Camera, Info } from 'lucide-react';
import DemoEvidenceModal from './DemoEvidenceModal';

export default function DemoEventsSection() {
  const [events, setEvents] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/demo/events');
      if (res.ok) {
        const data = await res.json();
        if (data.events) {
          setEvents(data.events);
        }
      }
    } catch (err) {
      console.warn("Failed to fetch demo events:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
    const interval = setInterval(fetchEvents, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200 card-shadow space-y-4">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-amber-100 border border-amber-200 rounded-lg text-amber-700">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-[#12355B]">
              Demonstration Traffic Alerts & Violation Intelligence
            </h3>
            <p className="text-xs text-slate-500 font-medium">
              Traffic events and captured evidence frames generated on demo streams.
            </p>
          </div>
        </div>

        <button
          onClick={fetchEvents}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-all"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Alerts</span>
        </button>
      </div>

      {events.length === 0 ? (
        <div className="p-8 text-center bg-slate-50 rounded-xl border border-slate-200 text-slate-500 text-xs space-y-1">
          <Info className="w-6 h-6 text-slate-400 mx-auto mb-2" />
          <p className="font-semibold text-slate-700">No traffic events detected in this demonstration.</p>
          <p className="text-[11px] text-slate-500">
            The AI engine is monitoring vehicle trajectories and density across demo scenarios.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {events.map((evt) => (
            <div
              key={evt.event_id}
              className="bg-slate-50 hover:bg-white rounded-xl p-4 border border-slate-200 hover:border-[#1976D2] card-shadow transition-all space-y-3 flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="px-2 py-0.5 bg-amber-100 text-amber-800 text-[10px] font-bold rounded font-mono border border-amber-200">
                    DEMO ALERT
                  </span>
                  <span className="text-[10px] font-mono text-slate-500 font-semibold">
                    {new Date(evt.timestamp).toLocaleTimeString()}
                  </span>
                </div>

                <div>
                  <h4 className="text-sm font-bold text-[#12355B]">
                    {evt.title || evt.event_type}
                  </h4>
                  <p className="text-xs text-slate-500 font-medium mt-0.5">
                    {evt.camera_id} · {evt.display_location || 'Recorded Dataset Footage'}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
                  <span className="px-2 py-0.5 bg-white text-slate-700 rounded border border-slate-200">
                    Class: <strong className="uppercase text-[#1976D2]">{evt.vehicle_class || 'car'}</strong>
                  </span>
                  {evt.track_id && (
                    <span className="px-2 py-0.5 bg-white text-slate-700 rounded border border-slate-200">
                      Track: <strong>#{evt.track_id}</strong>
                    </span>
                  )}
                </div>
              </div>

              <button
                onClick={() => setSelectedEvent(evt)}
                className="w-full py-2 bg-[#1976D2] hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 shadow-xs"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>VIEW EVIDENCE</span>
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Evidence Modal Popup */}
      {selectedEvent && (
        <DemoEvidenceModal
          eventItem={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}
    </div>
  );
}
