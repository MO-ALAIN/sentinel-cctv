import React, { useState } from 'react';
import CameraCard from './CameraCard';
import { Search, Filter, PlayCircle, StopCircle, Video } from 'lucide-react';

export default function CameraGrid({ cameras, onToggleConnection, onBulkConnect, onBulkDisconnect }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterMode, setFilterMode] = useState('ALL'); // ALL, ACTIVE, DISCONNECTED

  const filteredCameras = cameras.filter(cam => {
    const matchesSearch = cam.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          cam.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          cam.location.toLowerCase().includes(searchTerm.toLowerCase());
    
    if (!matchesSearch) return false;

    if (filterMode === 'ACTIVE') {
      return cam.connection_status === 'CONNECTED' || cam.connection_status === 'CONNECTING';
    }
    if (filterMode === 'DISCONNECTED') {
      return !cam.connection_status || cam.connection_status === 'DISCONNECTED';
    }
    return true;
  });

  return (
    <div className="flex flex-col gap-4">
      {/* Controls and Search Toolbar */}
      <div className="bg-[#111823] border border-[#1e2a3a] rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#7d8da3]" />
          <input
            type="text"
            placeholder="Search cameras by ID, name, or location..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#0a0e14] border border-[#1e2a3a] focus:border-blue-500 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-[#5c6b86] outline-none"
          />
        </div>

        {/* Filters and Bulk Actions */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Filter Pills */}
          <div className="flex items-center bg-[#0a0e14] border border-[#1e2a3a] rounded-lg p-1 text-xs">
            {['ALL', 'ACTIVE', 'DISCONNECTED'].map((mode) => (
              <button
                key={mode}
                onClick={() => setFilterMode(mode)}
                className={`px-3 py-1 rounded-md font-semibold transition ${
                  filterMode === mode
                    ? 'bg-blue-600 text-white'
                    : 'text-[#7d8da3] hover:text-white'
                }`}
              >
                {mode}
              </button>
            ))}
          </div>

          {/* Bulk Actions */}
          <button
            onClick={onBulkConnect}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-800 text-emerald-300 text-xs font-semibold rounded-lg transition"
          >
            <PlayCircle className="w-3.5 h-3.5" />
            Connect All
          </button>
          <button
            onClick={onBulkDisconnect}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-950/80 hover:bg-rose-900 border border-rose-800 text-rose-300 text-xs font-semibold rounded-lg transition"
          >
            <StopCircle className="w-3.5 h-3.5" />
            Disconnect All
          </button>
        </div>
      </div>

      {/* Camera Grid */}
      {filteredCameras.length === 0 ? (
        <div className="bg-[#111823] border border-[#1e2a3a] rounded-xl p-12 text-center text-[#7d8da3]">
          <Video className="w-12 h-12 mx-auto mb-3 opacity-30 text-blue-400" />
          <h3 className="text-base font-semibold text-white">No cameras match your criteria</h3>
          <p className="text-xs mt-1">Try adjusting your search query or filter options.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredCameras.map((cam) => (
            <CameraCard
              key={cam.id}
              camera={cam}
              onToggleConnection={onToggleConnection}
            />
          ))}
        </div>
      )}
    </div>
  );
}
