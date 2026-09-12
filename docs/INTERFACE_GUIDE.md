# Interface guide — 11 September 2026

The interface now opens on **Overview**, with three clear choices: view cameras, find a vehicle, or review alerts. The underlying camera, analytics, investigation, import/export and evidence features remain available.

## Where to find each task

| Task | Location |
|---|---|
| See current counts and choose a task | Overview |
| View, connect, disconnect or inspect a feed | Live Cameras; connected feeds appear first, six per page |
| Export actual recent vehicle detections with source/time information | Live Cameras → Export recent detections |
| Search a plate, filter its history, inspect evidence or export CSV | Find vehicle |
| Review evidence and acknowledge watchlist matches | Alerts |
| Add, edit, import or deactivate vehicles of interest | Watchlist |
| Add/edit cameras, search/filter records, show the map | Camera registry → Camera list & map |
| Import surveys, measure coverage, inspect/remove polygons and download results | Camera registry → Coverage |
| Import camera CSV, refresh organizer catalogue, export registry, see metadata gaps or audit history | Camera registry → Imports & reports |
| Previous monitoring dashboard | More tools → Monitoring dashboard |
| Traffic counts, density and flow | More tools → Traffic analytics |
| Traffic events and incidents | More tools → Incident review |
| Detailed source connection controls | More tools → Connection management |
| Recognition suitability assessment | More tools → Plate-reading assessment |
| Existing recorded scenarios and their controls | More tools → Recorded demos |
| Hardware, model readiness and detailed service counters | More tools → System status |

Registry records are paged ten at a time. Search and filters apply to the complete list; exports retain their existing scope. Map display, coverage calculations, metadata reports and history exports are preserved.

The global demo switch has been replaced by a separate Recorded demos page. Opening it no longer overrides unrelated pages. Browser Back/Forward and direct page links work, including `http://127.0.0.1:8000/dashboard/#vehicle-trace`. On phones, the menu opens with readable labels and supports Escape to close. Desktop navigation can still collapse.

The header refresh checks local state. Organizer catalogue import remains an explicit action in the registry and connection-management tools. Global technical banners and repeated counters have been consolidated; connection errors remain visible and full diagnostics stay in System status. No recognition accuracy or camera availability is inferred from this interface change.

## Verification and rollback

Browser checks cover the original onboarding, watchlist, vehicle-history, evidence-report download, alert acknowledgement and survey workflow. Additional checks cover every page, registry and live-camera pagination/search, map and import/report visibility, direct links, browser history, demo-independent navigation, collapsed navigation and the mobile menu.

The pre-change interface archive is `data/interface-before-20260910-132451.zip`. It contains the previous frontend source and browser scripts. The original full-project checkpoint is also preserved separately. Current government and public-source screen recordings are under docs/verification; the latest overview screenshots are under `docs/verification/organized-*.png`.
