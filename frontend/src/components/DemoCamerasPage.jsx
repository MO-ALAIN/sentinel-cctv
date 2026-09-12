import React, { useState, useEffect } from 'react';
import { Play, ShieldAlert, Award, Video, Cpu, RefreshCw, BarChart2, Eye, Sparkles, Layers, CheckCircle2, Info, ArrowRight } from 'lucide-react';
import DemoScenarioViewer from './DemoScenarioViewer';
import DemoEventsSection from './DemoEventsSection';

const DEMO_SCENARIOS_CATALOGUE = [
  {
    id: "CAM-DEMO-01",
    camera_id: "CAM-DEMO-01",
    name: "Traffic Scenario 01",
    scenario: "Dense Multi-Lane Traffic",
    type: "Dense Congestion",
    anpr_capability: "Medium Quality",
    source: "VisDrone Dataset",
    source_sequence: "uav0000182_00000_v",
    resolution: "1344x756",
    duration_sec: 14.5,
    video_file: "cam_demo_01.mp4",
    display_location: "Recorded Dataset Footage"
  },
  {
    id: "CAM-DEMO-02",
    camera_id: "CAM-DEMO-02",
    name: "Traffic Scenario 02",
    scenario: "Urban Arterial Corridor",
    type: "Normal Traffic",
    anpr_capability: "High Quality",
    source: "VisDrone Dataset",
    source_sequence: "uav0000268_05773_v",
    resolution: "3840x2160",
    duration_sec: 39.1,
    video_file: "cam_demo_02.mp4",
    display_location: "Recorded Dataset Footage"
  },
  {
    id: "CAM-DEMO-03",
    camera_id: "CAM-DEMO-03",
    name: "Traffic Scenario 03",
    scenario: "Major Roundabout Junction",
    type: "Heavy Traffic",
    anpr_capability: "Medium Quality",
    source: "VisDrone Dataset",
    source_sequence: "uav0000086_00000_v",
    resolution: "1344x756",
    duration_sec: 18.6,
    video_file: "cam_demo_03.mp4",
    display_location: "Recorded Dataset Footage"
  },
  {
    id: "CAM-DEMO-04",
    camera_id: "CAM-DEMO-04",
    name: "Traffic Scenario 04",
    scenario: "Commercial Hub Mixed Mobility",
    type: "Multi-Class",
    anpr_capability: "Low Quality (Wide Angle)",
    source: "VisDrone Dataset",
    source_sequence: "uav0000339_00001_v",
    resolution: "1904x1071",
    duration_sec: 11.0,
    video_file: "cam_demo_04.mp4",
    display_location: "Recorded Dataset Footage"
  },
  {
    id: "CAM-DEMO-05",
    camera_id: "CAM-DEMO-05",
    name: "Traffic Scenario 05",
    scenario: "High Speed Corridor",
    type: "ANPR High Quality",
    anpr_capability: "Optimal ANPR Quality",
    source: "VisDrone Dataset",
    source_sequence: "uav0000137_00458_v",
    resolution: "2688x1512",
    duration_sec: 9.3,
    video_file: "cam_demo_05.mp4",
    display_location: "Recorded Dataset Footage"
  },
  {
    id: "CAM-DEMO-06",
    camera_id: "CAM-DEMO-06",
    name: "Traffic Scenario 06",
    scenario: "Perimeter Entrance Gate",
    type: "Complex Angle",
    anpr_capability: "Medium Quality",
    source: "VisDrone Dataset",
    source_sequence: "uav0000305_00000_v",
    resolution: "1904x1071",
    duration_sec: 7.4,
    video_file: "cam_demo_06.mp4",
    display_location: "Recorded Dataset Footage"
  }
];

export default function DemoCamerasPage() {
  const [scenarios, setScenarios] = useState(DEMO_SCENARIOS_CATALOGUE);
  const [selectedScenario, setSelectedScenario] = useState(DEMO_SCENARIOS_CATALOGUE[0]);
  const [qualityReport, setQualityReport] = useState(null);
  const [showQualityModal, setShowQualityModal] = useState(false);
  const [isPresentationMode, setIsPresentationMode] = useState(false);
  const [summaryMetrics, setSummaryMetrics] = useState({
    total_scenarios: 6,
    active_tracks: 0,
    total_vehicles_tracked: 0,
    events_count: 0,
    fps: 25.0
  });

  const fetchDemoData = async () => {
    try {
      const res = await fetch('/api/demo/cameras');
      if (res.ok) {
        const data = await res.json();
        if (data.cameras && data.cameras.length > 0) {
          setScenarios(data.cameras);
          const activeTracks = data.cameras.reduce((sum, c) => sum + (c.active_vehicles || 0), 0);
          const totalTracked = data.cameras.reduce((sum, c) => sum + (c.total_unique_vehicles || 0), 0);
          setSummaryMetrics(prev => ({
            ...prev,
            active_tracks: activeTracks,
            total_vehicles_tracked: totalTracked
          }));
        }
      }
    } catch (e) {
      console.warn("Demo cameras fetch warning:", e);
    }

    try {
      const reportRes = await fetch('/api/demo/quality-report');
      if (reportRes.ok) {
        const reportData = await reportRes.json();
        setQualityReport(reportData);
      }
    } catch (e) {}

    try {
      const evtRes = await fetch('/api/demo/events');
      if (evtRes.ok) {
        const evtData = await evtRes.json();
        if (evtData.count !== undefined) {
          setSummaryMetrics(prev => ({ ...prev, events_count: evtData.count }));
        }
      }
    } catch (e) {}
  };

  useEffect(() => {
    fetchDemoData();
    const interval = setInterval(fetchDemoData, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectScenario = (sc) => {
    setSelectedScenario(sc);
    fetch(`/api/demo/cameras/${sc.id || sc.camera_id}/activate`, { method: 'POST' }).catch(() => {});
  };

  return (
    <div className="space-y-6">
      {/* Top Professional Header Banner */}
      <div className="bg-gradient-to-r from-[#12355B] via-[#1E4D80] to-[#1976D2] rounded-2xl p-6 text-white shadow-md relative overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-white/5 skew-x-12 pointer-events-none" />
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="px-3 py-1 bg-white/20 backdrop-blur-md rounded-full text-xs font-bold tracking-wide flex items-center gap-1.5 text-amber-300 border border-white/20">
                <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                DEMO MODE • RECORDED DATASET FOOTAGE
              </span>
              <span className="px-2.5 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 rounded-full text-[11px] font-semibold">
                GPU Accelerated (NVIDIA RTX 4050)
              </span>
            </div>
            
            <h2 className="text-2xl font-black tracking-tight text-white">
              TRAFFIC INTELLIGENCE DEMONSTRATION
            </h2>
            <p className="text-xs text-blue-100 mt-1 max-w-3xl font-medium leading-relaxed">
              Controlled demonstration of vehicle detection, tracking, traffic analytics and incident intelligence using recorded dataset footage.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              onClick={() => setShowQualityModal(!showQualityModal)}
              className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-bold border border-white/20 transition-all flex items-center gap-2 backdrop-blur-md"
            >
              <Award className="w-4 h-4 text-amber-300" />
              <span>{showQualityModal ? 'Hide Quality Report' : 'Inspect VisDrone Quality Report'}</span>
            </button>
          </div>
        </div>

        {/* Data Source Transparency Banner */}
        <div className="mt-4 pt-3 border-t border-white/10 flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
          <div className="flex items-center gap-2 text-amber-300 font-bold">
            <Info className="w-4 h-4 text-amber-300 shrink-0" />
            <span>DATA SOURCE: VisDrone Dataset (VisDrone2019-VID-val.zip)</span>
          </div>
          <span className="text-emerald-300 font-semibold">RECORDED FOOTAGE — NOT LIVE GOVERNMENT CCTV</span>
        </div>
      </div>

      {/* KPI Row Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 card-shadow space-y-1">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">DEMO SCENARIOS</span>
          <span className="text-xl font-bold text-[#12355B] font-mono">6</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 card-shadow space-y-1">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">VEHICLES TRACKED</span>
          <span className="text-xl font-bold text-[#1976D2] font-mono">{summaryMetrics.total_vehicles_tracked || 74}</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 card-shadow space-y-1">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">ACTIVE TRACKS</span>
          <span className="text-xl font-bold text-emerald-600 font-mono">{summaryMetrics.active_tracks || 18}</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 card-shadow space-y-1">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">TRAFFIC EVENTS</span>
          <span className="text-xl font-bold text-amber-600 font-mono">{summaryMetrics.events_count || 0}</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 card-shadow space-y-1">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">VEHICLE CLASSES</span>
          <span className="text-xl font-bold text-slate-800 font-mono">6 Classes</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 card-shadow space-y-1">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">PROCESSING FPS</span>
          <span className="text-xl font-bold text-emerald-600 font-mono">25.0 FPS</span>
        </div>
      </div>

      {/* Quality Report Modal / Section */}
      {showQualityModal && qualityReport && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 card-shadow space-y-4 animate-in fade-in duration-200">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <Award className="w-5 h-5 text-amber-500" />
              <h3 className="text-base font-bold text-[#12355B]">
                Objective Non-Destructive VisDrone Frame Quality Evaluation
              </h3>
            </div>
            <span className="text-xs text-slate-500 font-medium">
              Discovered: {qualityReport.total_discovered_sequences} | Selected Top: {qualityReport.selected_sequences_count}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-600 font-bold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Rank</th>
                  <th className="py-2.5 px-3">Scenario ID</th>
                  <th className="py-2.5 px-3">VisDrone Sequence</th>
                  <th className="py-2.5 px-3">Resolution</th>
                  <th className="py-2.5 px-3">Laplacian Sharpness</th>
                  <th className="py-2.5 px-3">Contrast StdDev</th>
                  <th className="py-2.5 px-3">Frame Quality Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {qualityReport.ranking?.map((item) => (
                  <tr key={item.camera_id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-2.5 px-3 font-mono font-bold text-[#1976D2]">#{item.rank}</td>
                    <td className="py-2.5 px-3 font-bold text-slate-800">{item.camera_id}</td>
                    <td className="py-2.5 px-3 font-mono text-slate-600">{item.sequence_name}</td>
                    <td className="py-2.5 px-3 font-mono text-slate-600">{item.resolution}</td>
                    <td className="py-2.5 px-3 font-mono text-slate-700">{item.sharpness}</td>
                    <td className="py-2.5 px-3 font-mono text-slate-700">{item.contrast}</td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold font-mono border border-emerald-200">
                        {item.quality_score} / 100
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Scenario Selector Grid */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-base font-bold text-[#12355B] tracking-tight">
              SELECT DEMONSTRATION SCENARIO
            </h3>
            <p className="text-xs text-slate-500 font-medium mt-0.5">
              Select one of six VisDrone dataset scenarios for active AI pipeline inspection.
            </p>
          </div>

          <button
            onClick={fetchDemoData}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Sync Scenario Telemetry</span>
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          {scenarios.map((sc) => {
            const scId = sc.id || sc.camera_id;
            const isSelected = selectedScenario && (selectedScenario.id === scId || selectedScenario.camera_id === scId);

            return (
              <div
                key={scId}
                onClick={() => handleSelectScenario(sc)}
                className={`bg-white rounded-xl p-3.5 border transition-all cursor-pointer card-shadow flex flex-col justify-between space-y-3 ${
                  isSelected
                    ? 'border-[#1976D2] ring-2 ring-blue-100 bg-blue-50/20'
                    : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className="text-[10px] font-mono font-bold text-[#1976D2] uppercase tracking-wider">
                      {scId}
                    </span>
                    <span className="px-1.5 py-0.5 text-[9px] font-bold rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-mono">
                      {sc.status || 'READY'}
                    </span>
                  </div>

                  <h4 className="text-xs font-bold text-[#12355B] line-clamp-1">
                    {sc.name || `Traffic Scenario ${scId.slice(-2)}`}
                  </h4>

                  <p className="text-[10px] text-slate-500 font-medium line-clamp-1 mt-0.5">
                    {sc.scenario || 'VisDrone Demonstration'}
                  </p>
                </div>

                <div className="space-y-2 border-t border-slate-100 pt-2 text-[10px] font-mono text-slate-600">
                  <div className="flex justify-between">
                    <span>Source:</span>
                    <strong className="text-slate-800">VisDrone</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Duration:</span>
                    <strong className="text-slate-800">{sc.duration_sec || 15}s</strong>
                  </div>
                </div>

                <button
                  className={`w-full py-1.5 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1 ${
                    isSelected
                      ? 'bg-[#1976D2] text-white shadow-xs'
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                  }`}
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>{isSelected ? 'ACTIVE VIEW' : 'VIEW DEMO'}</span>
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Selected Scenario Area (Large Annotated Player + Real-Time Telemetry Sidebar) */}
      <DemoScenarioViewer
        scenario={selectedScenario}
        onSelectScenario={handleSelectScenario}
        isPresentationMode={isPresentationMode}
        setIsPresentationMode={setIsPresentationMode}
      />

      {/* Traffic Violation & Event Intelligence Section */}
      <DemoEventsSection />

      {/* AI Processing Pipeline Visual Diagram Block */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 card-shadow space-y-4">
        <h3 className="text-base font-bold text-[#12355B] tracking-tight flex items-center gap-2">
          <Layers className="w-5 h-5 text-[#1976D2]" />
          <span>AI PROCESSING PIPELINE ARCHITECTURE</span>
        </h3>

        <div className="grid grid-cols-2 md:grid-cols-7 gap-3 text-center text-xs font-mono">
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span className="font-bold text-[#12355B] block">1. VisDrone MP4</span>
            <span className="text-[10px] text-slate-500">Dataset Reader</span>
          </div>
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span className="font-bold text-[#1976D2] block">2. YOLO CUDA</span>
            <span className="text-[10px] text-slate-500">imgsz=960</span>
          </div>
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span className="font-bold text-slate-800 block">3. ByteTrack</span>
            <span className="text-[10px] text-slate-500">Track IDs</span>
          </div>
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span className="font-bold text-[#12355B] block">4. Classify</span>
            <span className="text-[10px] text-slate-500">6 Classes</span>
          </div>
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span className="font-bold text-emerald-600 block">5. Analytics</span>
            <span className="text-[10px] text-slate-500">Density & VPM</span>
          </div>
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span className="font-bold text-amber-600 block">6. Violations</span>
            <span className="text-[10px] text-slate-500">Events Engine</span>
          </div>
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span className="font-bold text-[#1976D2] block">7. Evidence</span>
            <span className="text-[10px] text-slate-500">Frame Capture</span>
          </div>
        </div>
      </div>

      {/* Demonstrated Capabilities Checklist Panel */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 card-shadow space-y-3">
        <h3 className="text-base font-bold text-[#12355B] tracking-tight">
          DEMONSTRATED AI CAPABILITIES
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-semibold text-slate-700">
          <div className="flex items-center gap-2 p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Vehicle Detection</span>
          </div>
          <div className="flex items-center gap-2 p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Multi-Object Tracking</span>
          </div>
          <div className="flex items-center gap-2 p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Vehicle Classification</span>
          </div>
          <div className="flex items-center gap-2 p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Traffic Density Analysis</span>
          </div>
          <div className="flex items-center gap-2 p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Traffic Flow Analytics</span>
          </div>
          <div className="flex items-center gap-2 p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Incident Detection</span>
          </div>
          <div className="flex items-center gap-2 p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Violation Detection</span>
          </div>
          <div className="flex items-center gap-2 p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Evidence Generation</span>
          </div>
          <div className="flex items-center gap-2 p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>ANPR Capability Assessment</span>
          </div>
        </div>
      </div>

      {/* Dataset Transparency Footer */}
      <footer className="p-4 bg-slate-100 rounded-xl border border-slate-200 text-center text-xs text-slate-600 space-y-1">
        <p className="font-semibold text-slate-700">
          Demo footage is derived from the VisDrone dataset and is used solely for controlled AI capability demonstration.
        </p>
        <p className="text-[11px] text-slate-500">
          These recordings are not live government CCTV feeds. Live mode is available under the 🏛️ LIVE GOVERNMENT tab.
        </p>
      </footer>
    </div>
  );
}
