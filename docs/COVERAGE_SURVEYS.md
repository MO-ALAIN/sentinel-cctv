# Surveyed coverage

The Registry & GIS page imports GeoJSON polygons and measures how much of each verified area boundary intersects the union of verified camera footprints. Overlapping footprints count once. Representative geometry is visible but excluded from measurements. Missing verified boundaries produce an explicit unavailable result.

Each feature requires `properties.id`, `name`, `kind` (`AREA` or `CAMERA`) and `provenance` (`VERIFIED` or `REPRESENTATIVE`). A CAMERA feature also requires an existing `camera_id`. Geometry must be a valid 2D Polygon or MultiPolygon in longitude/latitude. Imports validate all features before writing; duplicate IDs and invalid camera references are rejected. IDs update existing features. Imports and removals require admin access and create audit entries.

Measurements use the EPSG:6933 equal-area projection. A surveyed footprint describes geometric coverage; it does not establish that a camera is operational, a vehicle is unobstructed or a plate is readable. The current organizer catalogue provides no verified coordinates or footprints, so none are invented in the main database.

API: `GET/POST /api/registry/coverage`, `GET /api/registry/coverage/gaps`, `DELETE /api/registry/coverage/{id}`. The interface provides import, measure, map overlays, removal and JSON report download. Reports include surveyed/covered/uncovered square metres and uncovered polygons.

Automated verification uses an isolated synthetic rectangle with two overlapping half-area footprints. Its measured union is 50%, including after adding a representative full-area footprint. Browser fixture surveys are synthetic even though their test-only provenance field exercises the VERIFIED branch; they are never imported into the main registry.
