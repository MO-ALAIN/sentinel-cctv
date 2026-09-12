# Sentinel — CCTV Registry and Vehicle Investigation

A Model 1 + Model 2 implementation for the Gujarat Police Innovation Challenge.
It combines camera onboarding/GIS, direct video ingestion, vehicle detection and
tracking, durable plate observations, representative watchlists and operator alerts.

See [current results and remaining submission work](docs/CURRENT_STATUS.md) for
the verified 11 September status, preview instructions and evidence artifacts.

## Collaborate now; optional hosting later

The full application runs locally for free using your own hardware. Cloud hosting
is currently deferred; the saved competition guide makes a hosted URL optional.
Your friend can clone this public repository and you can add them as a collaborator.

For future hosting, see [Render deployment instructions](docs/DEPLOYMENT.md). The Blueprint builds
this React + FastAPI application with CPU AI models and persistent storage.
It requires paid compute and disk; review the quoted cost before activating it.
GitHub stores the code; Render serves the website. GitHub Pages cannot run this backend.

After deployment, push reviewed changes to `main`. Render is configured to deploy
after GitHub checks pass. Keep credentials in Render Environment, never in GitHub.

## Run on Windows

From this repository:

```powershell
.\setup.ps1
.\start.ps1
```

Open http://127.0.0.1:8000/dashboard/ . Without AI packages/weights, registry,
saved investigations and video viewing remain available and AI is explicitly
reported unavailable.

For the RTX 3050 / compatible CUDA driver:

```powershell
.\setup.ps1 -WithAI
.\.venv\Scripts\python.exe backend\setup_models.py --plate-detector
.\start.ps1
```

This installs the tested PyTorch 2.6 / CUDA 12.4 family. Confirm GPU support with
the actual installed driver. Dependencies/downloads use project temporary/cache
paths so a full system drive does not prevent setup. The optional plate-detector
flag installs a pinned third-party localization baseline. See
[model provenance](docs/MODEL_PROVENANCE.md); target-camera accuracy still needs evaluation.

On this workstation you can also double-click **START_PREVIEW.cmd** and keep its
window open. It serves the built interface at http://127.0.0.1:8000/dashboard/ .
Previously connected network sources resume after restart; other sources stay stopped.
The local preview process must have network access to reach organizer feeds.

## Configure sources

Copy backend/.env.example to backend/.env and supply your authorized organizer
endpoint/password locally. Credentials must never be committed. Catalogue refresh
is explicit; the application never registers accounts or invents camera lists.

For a recording, put the original file under scratch/ and onboard its filename
in Registry & GIS with source type RECORDED. Supply its original UTC recording
start if known. For organizer streams select GOVERNMENT_REPLAY. LIVE means an
actual current camera source. Use verified or explicitly representative coordinates.
Blank source input while editing preserves the existing private source.

All persistent paths are independent of the shell working directory. Set
CCTV_DB_PATH, CCTV_DATA_DIR, CCTV_MEDIA_DIR or CCTV_DEMO_DIR in the process
environment before launch to override them. Database default: repository root
cctv_surveillance.db. Evidence default: data/evidence/.

## Operator workflow

1. Onboard cameras manually, through CSV, or the authorized organizer catalogue.
2. Connect a source and inspect its real status in Live Cameras.
3. Add representative watchlist records.
4. Process suitable footage. Confirmed plate observations automatically persist
   and generate watchlist alerts.
5. Search Vehicle Trace, inspect ordered camera visits/evidence, filter by time
   or source and export CSV.
6. Acknowledge alerts and inspect audit history.
7. Import verified area boundaries and camera footprints to measure surveyed
   geographic coverage. See [survey format and limits](docs/COVERAGE_SURVEYS.md).

Frames must contain readable plate detail. Recognition needs agreement between
independent frames; no model is claimed to reconstruct absent characters.
A ByteTrack ID is camera/session-local. Map links show observed camera order,
not the exact roads travelled.

## Access control

Default server binding is loopback. Unconfigured authentication allows only
loopback API access. For authenticated operation set CCTV_ADMIN_PASSWORD and
optionally CCTV_OPERATOR_PASSWORD / CCTV_VIEWER_PASSWORD in the launch
environment, then sign in using admin, operator or viewer. Put shared deployments
behind HTTPS. Department-specific query isolation and organizational OIDC remain
deployment work; this prototype must not be described as a hardened statewide system.

## Development and tests

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest
cd ..\frontend
npm run build
```

If C: has no space, set TEMP and TMP to a writable E: directory and pass a unique
E: path to pytest --basetemp.

The legacy test_*.py scripts outside backend/tests include network/GPU diagnostic
runs. They are not the offline acceptance suite. Browser checks use
frontend/browser-check.mjs and an isolated fixture server on 8011.

## Submission documents

- docs/REQUIREMENTS_AND_EVIDENCE.md: criterion-by-criterion status and checklist.
- docs/HIGH_LEVEL_DESIGN.md: implemented architecture and proposed scale path.
- docs/DEMO_RUNBOOK.md: actual demonstration sequence and recovery.
- docs/SOLUTION_PRESENTATION.pdf: presentation, with pending validations identified.
- docs/verification/: development test screenshots, using synthetic fixtures.
- CONTRACT.md: API contract and additive implementation extensions.

## Current evidence and limits

Backend acceptance tests and a production frontend build pass. Real Edge browser
checks cover camera onboarding, watchlist changes, two-camera synthetic trace,
CSV download and alert acknowledgement. The supplied controlled MP4 passes
ingestion and worker shutdown. These tests do not establish government-feed ANPR
accuracy or a demonstrated multi-camera production capacity.

Government catalogue access requires an authorized sign-in. The six externally
referenced VisDrone files were not supplied. Historic Word documents and earlier
README performance claims are not current measured acceptance evidence.
Use the evidence register before any submission or production-readiness claim.

## Component licenses

Review each dependency and model license for the intended deployment. In
particular, Ultralytics licensing and model provenance must be assessed; a project
README license label does not override dependency/model terms.
