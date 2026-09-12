import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const EMPTY = [];

export default function GeoMap({ cameras = EMPTY, route = EMPTY, surveys = EMPTY, uncovered = EMPTY, selectedId, onSelect }) {
  const element = useRef(null); const map = useRef(null); const layer = useRef(null);
  const [tileError, setTileError] = useState(false);
  const bounds = useRef(null), geometry = useRef('');
  useEffect(() => {
    map.current = L.map(element.current).setView([22.6, 71.6], 7);
    L.tileLayer(import.meta.env.VITE_MAP_TILES || 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors', maxZoom: 19,
    }).on('tileerror', () => setTileError(true)).addTo(map.current);
    layer.current = L.layerGroup().addTo(map.current);
    const observer = new ResizeObserver(() => {
      map.current?.invalidateSize({ pan:false });
      if (bounds.current) map.current?.fitBounds(bounds.current,{padding:[35,35],maxZoom:13,animate:false});
    }); observer.observe(element.current);
    return () => { observer.disconnect(); map.current.remove(); map.current = null; };
  }, []);
  useEffect(() => {
    if (!layer.current) return;
    layer.current.clearLayers();
    const rows = route.length ? route : cameras;
    const points = [];
    [...surveys, ...uncovered].forEach(feature => {
      const props = feature.properties || {};
      const color = props.kind === 'GAP' ? '#dc2626' : props.provenance === 'REPRESENTATIVE' ? '#a16207' : props.kind === 'AREA' ? '#64748b' : '#16a34a';
      const shape = L.geoJSON(feature, { style: { color, weight: 2, fillOpacity: props.kind === 'AREA' ? .03 : .2 } }).addTo(layer.current);
      const label = document.createElement('span'); label.textContent = `${props.name || props.id} · ${props.kind} · ${props.provenance || 'VERIFIED'}`;
      shape.bindPopup(label);
      const extent = shape.getBounds();
      if (extent.isValid()) points.push([extent.getSouth(), extent.getWest()], [extent.getNorth(), extent.getEast()]);
    });
    rows.forEach((row, i) => {
      if (row.lat == null || row.lon == null || !Number.isFinite(Number(row.lat)) || !Number.isFinite(Number(row.lon))) return;
      const point = [Number(row.lat), Number(row.lon)]; points.push(point);
      const color = row.id === selectedId ? '#f97316' : row.geo_source === 'VERIFIED' ? '#1976d2' : '#a16207';
      const marker = L.circleMarker(point, { radius: route.length ? 9 : 7, color, fillColor: color, fillOpacity: .8, weight: 2 }).addTo(layer.current);
      const popup = document.createElement('div');
      const title = document.createElement('strong'); title.textContent = route.length ? `${i + 1}. ${row.camera_id}` : row.name || row.id;
      const detail = document.createElement('p'); detail.textContent = `${row.location || 'Location unavailable'} · ${row.geo_source || 'UNKNOWN'} coordinates`;
      popup.append(title, detail); marker.bindPopup(popup); marker.on('click', () => onSelect?.(row));
      if (route.length) marker.bindTooltip(String(i + 1), { permanent: true, direction: 'top' });
      if (row.id === selectedId) marker.openPopup();
    });
    if (route.length > 1) {
      // Never draw over a missing-coordinate observation: it is a gap in the evidence.
      for (let i = 1; i < route.length; i++) {
        const a = route[i - 1], b = route[i];
        if ([a.lat, a.lon, b.lat, b.lon].every(v => v != null && Number.isFinite(Number(v))))
          L.polyline([[a.lat, a.lon], [b.lat, b.lon]], { color: '#1976d2', dashArray: '6 8', weight: 3 }).addTo(layer.current);
      }
    }
    const signature = JSON.stringify(points);
    if (!points.length) { bounds.current = null; geometry.current = ''; }
    if (points.length && signature !== geometry.current) {
      geometry.current = signature;
      bounds.current = L.latLngBounds(points);
      map.current.invalidateSize({pan:false});
      map.current.fitBounds(bounds.current, { padding: [35, 35], maxZoom: 13, animate:false });
    }
  }, [cameras, route, surveys, uncovered, selectedId]);
  return <div className="geo-wrap"><div ref={element} className="geo-map" aria-label="Camera and vehicle observation map" />
    {tileError && <p className="map-notice">Basemap unavailable. Observation markers and the table remain available.</p>}
    <div className="map-legend"><span>🔵 Verified coordinates</span><span>🟤 Unverified / representative</span>{route.length > 0 && <span>Dashed lines show observation order, not the exact road travelled.</span>}</div>
    {(surveys.length > 0 || uncovered.length > 0) && <div className="map-legend"><span>Green: surveyed footprint</span><span>Red: uncovered area</span><span>Grey: survey boundary</span></div>}
  </div>;
}
